from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1._common import commit_or_conflict, get_or_404, now_utc, require_exists
from app.db.models import Course, School
from app.db.session import get_db
from app.schemas.course import CourseCreate, CourseResponse, CourseUpdate

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("", response_model=list[CourseResponse])
def list_courses(school_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Course).order_by(Course.id)
    if school_id is not None:
        stmt = stmt.where(Course.school_id == school_id)
    return db.scalars(stmt).all()


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    require_exists(db, School, payload.school_id, "school_id")
    now = now_utc()
    course = Course(created_at=now, updated_at=now, **payload.model_dump())
    db.add(course)
    commit_or_conflict(db)
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Course, course_id)


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(course_id: int, payload: CourseUpdate, db: Session = Depends(get_db)):
    course = get_or_404(db, Course, course_id)
    values = payload.model_dump(exclude_unset=True)
    if "school_id" in values:
        require_exists(db, School, values["school_id"], "school_id")
    for key, value in values.items():
        setattr(course, key, value)
    course.updated_at = now_utc()
    commit_or_conflict(db)
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = get_or_404(db, Course, course_id)
    db.delete(course)
    commit_or_conflict(db)
