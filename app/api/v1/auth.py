"""Login, sessions and role checks.

Roles:

* ``ADMIN``: everything, including managing user accounts.
* ``COORDINATOR``: everything except user accounts (data, constraints,
  runs, exports).
* ``FACULTY``: read-only; sees only their own timetable.

The session is an HttpOnly cookie (``SameSite=Lax``) so browser downloads
and PDF links work; API clients may send the same token as
``Authorization: Bearer <token>``. The first admin is created through
``POST /auth/setup``, which only works while there are no users.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_token,
    hash_password,
    read_token,
    token_matches_password,
    verify_password,
)
from app.db.models import Faculty, User, UserRole
from app.db.session import get_db
from app.domain.timetable_views import designation_label

COOKIE_NAME = "tt_session"
STAFF_ROLES = frozenset({UserRole.ADMIN, UserRole.COORDINATOR})

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _token_from(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(COOKIE_NAME)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """The signed-in user, or 401."""

    token = _token_from(request)
    parsed = read_token(token) if token else None
    user = db.get(User, parsed[0]) if parsed else None

    if (
        user is None
        or not user.is_active
        or not token_matches_password(parsed[1], user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def require_staff(user: User = Depends(get_current_user)) -> User:
    """Administrators and coordinators."""

    if not is_staff(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and coordinators can do this",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can do this"
        )
    return user


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class SetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    full_name: str = Field(default="", max_length=150)
    password: str = Field(min_length=8, max_length=200)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


def user_payload(user: User, db: Session) -> dict:
    faculty = None
    if user.faculty_employee_id:
        member = db.scalar(select(Faculty).where(Faculty.employee_id == user.faculty_employee_id))
        if member is not None:
            faculty = {
                "employee_id": member.employee_id,
                "name": member.name,
                "designation": member.designation.value,
                "designation_label": designation_label(member.designation.value),
            }
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value,
        "faculty_employee_id": user.faculty_employee_id,
        "faculty": faculty,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


def _issue_session(response: Response, user: User) -> str:
    max_age = settings.session_hours * 3600
    token = create_token(user.id, user.password_hash, max_age)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return token


def find_user(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.username) == username.strip().lower()))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status")
def auth_status(db: Session = Depends(get_db)) -> dict:
    """Public: whether the first administrator still has to be created."""

    return {"needs_setup": (db.scalar(select(func.count()).select_from(User)) or 0) == 0}


@router.post("/setup", status_code=status.HTTP_201_CREATED)
def setup_first_admin(
    payload: SetupRequest, response: Response, db: Session = Depends(get_db)
) -> dict:
    """Create the first administrator. Refused once any user exists."""

    if db.scalar(select(func.count()).select_from(User)):
        raise HTTPException(status_code=409, detail="Setup is already complete; sign in instead")
    now = datetime.now(UTC)
    user = User(
        username=payload.username.strip(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN,
        last_login_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    token = _issue_session(response, user)
    return {"user": user_payload(user, db), "token": token}


@router.post("/login")
def login(payload: Credentials, response: Response, db: Session = Depends(get_db)) -> dict:
    user = find_user(db, payload.username)
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Wrong username or password")
    user.last_login_at = datetime.now(UTC)
    db.commit()
    token = _issue_session(response, user)
    return {"user": user_payload(user, db), "token": token}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return user_payload(user, db)


@router.post("/password")
def change_password(
    payload: PasswordChange,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is wrong")
    user.password_hash = hash_password(payload.new_password)
    user.updated_at = datetime.now(UTC)
    db.commit()
    _issue_session(response, user)
    return user_payload(user, db)
