"""User accounts (administrators only)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.auth import find_user, require_admin, user_payload
from app.core.security import generate_password, hash_password
from app.db.models import Faculty, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(require_admin)])


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    full_name: str = Field(default="", max_length=150)
    password: str = Field(min_length=8, max_length=200)
    role: UserRole
    faculty_employee_id: str | None = Field(default=None, max_length=50)
    is_active: bool = True

    @model_validator(mode="after")
    def _faculty_needs_link(self):
        if self.role == UserRole.FACULTY and not self.faculty_employee_id:
            raise ValueError("Faculty accounts must be linked to a faculty employee ID")
        return self


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=100)
    full_name: str | None = Field(default=None, max_length=150)
    password: str | None = Field(default=None, min_length=8, max_length=200)
    role: UserRole | None = None
    faculty_employee_id: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


def _check_faculty(db: Session, employee_id: str | None) -> None:
    if (
        employee_id
        and db.scalar(select(Faculty.id).where(Faculty.employee_id == employee_id)) is None
    ):
        raise HTTPException(
            status_code=404, detail=f"No faculty member with employee ID {employee_id}"
        )


def _check_username(db: Session, username: str, user_id: int | None = None) -> None:
    existing = find_user(db, username)
    if existing is not None and existing.id != user_id:
        raise HTTPException(status_code=409, detail=f"Username {username} is already taken")


def _active_admins(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        )
        or 0
    )


@router.get("")
def list_users(db: Session = Depends(get_db)) -> list[dict]:
    return [user_payload(user, db) for user in db.scalars(select(User).order_by(User.username))]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> dict:
    _check_username(db, payload.username)
    _check_faculty(db, payload.faculty_employee_id)
    now = datetime.now(UTC)
    user = User(
        username=payload.username.strip(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        faculty_employee_id=payload.faculty_employee_id or None,
        is_active=payload.is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    return user_payload(user, db)


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    changes = payload.model_dump(exclude_unset=True)
    if "username" in changes:
        _check_username(db, changes["username"], user.id)
        user.username = changes["username"].strip()
    if "full_name" in changes:
        user.full_name = (changes["full_name"] or "").strip()
    if "faculty_employee_id" in changes:
        _check_faculty(db, changes["faculty_employee_id"])
        user.faculty_employee_id = changes["faculty_employee_id"] or None
    if changes.get("password"):
        user.password_hash = hash_password(changes["password"])

    demoting = (
        changes.get("role") not in (None, UserRole.ADMIN) or changes.get("is_active") is False
    )
    if user.role == UserRole.ADMIN and demoting and _active_admins(db) <= 1:
        raise HTTPException(status_code=409, detail="Keep at least one active administrator")
    if user.id == current.id and demoting:
        raise HTTPException(status_code=409, detail="You cannot remove your own admin access")
    if changes.get("role") is not None:
        user.role = changes["role"]
    if changes.get("is_active") is not None:
        user.is_active = changes["is_active"]

    if user.role == UserRole.FACULTY and not user.faculty_employee_id:
        raise HTTPException(
            status_code=422, detail="Faculty accounts must be linked to a faculty member"
        )

    user.updated_at = datetime.now(UTC)
    db.commit()
    return user_payload(user, db)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int, db: Session = Depends(get_db), current: User = Depends(require_admin)
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    if user.id == current.id:
        raise HTTPException(status_code=409, detail="You cannot delete your own account")
    if user.role == UserRole.ADMIN and user.is_active and _active_admins(db) <= 1:
        raise HTTPException(status_code=409, detail="Keep at least one active administrator")
    db.delete(user)
    db.commit()


@router.post("/faculty-accounts", status_code=status.HTTP_201_CREATED)
def create_faculty_accounts(db: Session = Depends(get_db)) -> dict:
    """Create a FACULTY login for every active faculty member without one.

    The username is the employee ID. Generated passwords are returned once
    (they are stored only as hashes) so they can be handed out.
    """

    linked = set(
        db.scalars(select(User.faculty_employee_id).where(User.faculty_employee_id.is_not(None)))
    )
    now = datetime.now(UTC)
    created = []
    for member in db.scalars(
        select(Faculty).where(Faculty.is_active.is_(True)).order_by(Faculty.employee_id)
    ):
        if member.employee_id in linked or find_user(db, member.employee_id) is not None:
            continue
        password = generate_password()
        db.add(
            User(
                username=member.employee_id,
                full_name=member.name,
                password_hash=hash_password(password),
                role=UserRole.FACULTY,
                faculty_employee_id=member.employee_id,
                created_at=now,
                updated_at=now,
            )
        )
        db.flush()
        created.append(
            {
                "username": member.employee_id,
                "full_name": member.name,
                "email": member.email,
                "password": password,
            }
        )
    db.commit()
    return {"created": created}
