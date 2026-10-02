from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1._common import commit_or_conflict, get_or_404, now_utc, require_exists
from app.db.models import Faculty, School
from app.db.session import get_db
from app.schemas.faculty import FacultyCreate, FacultyResponse, FacultyUpdate

router = APIRouter(prefix="/faculty", tags=["Faculty"])


@router.get("", response_model=list[FacultyResponse])
def list_faculty(school_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Faculty).order_by(Faculty.id)
    if school_id is not None:
        stmt = stmt.where(Faculty.school_id == school_id)
    return db.scalars(stmt).all()


@router.post("", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def create_faculty(payload: FacultyCreate, db: Session = Depends(get_db)):
    require_exists(db, School, payload.school_id, "school_id")
    now = now_utc()
    faculty = Faculty(created_at=now, updated_at=now, **payload.model_dump())
    db.add(faculty)
    commit_or_conflict(db)
    db.refresh(faculty)
    return faculty


@router.get("/{faculty_id}", response_model=FacultyResponse)
def get_faculty(faculty_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Faculty, faculty_id)


@router.patch("/{faculty_id}", response_model=FacultyResponse)
def update_faculty(faculty_id: int, payload: FacultyUpdate, db: Session = Depends(get_db)):
    faculty = get_or_404(db, Faculty, faculty_id)
    values = payload.model_dump(exclude_unset=True)
    if "school_id" in values:
        require_exists(db, School, values["school_id"], "school_id")
    for key, value in values.items():
        setattr(faculty, key, value)
    faculty.updated_at = now_utc()
    commit_or_conflict(db)
    db.refresh(faculty)
    return faculty


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(faculty_id: int, db: Session = Depends(get_db)):
    faculty = get_or_404(db, Faculty, faculty_id)
    db.delete(faculty)
    commit_or_conflict(db)
