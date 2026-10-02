from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1._common import commit_or_conflict, get_or_404, now_utc
from app.db.models import School
from app.db.session import get_db
from app.schemas.school import SchoolCreate, SchoolResponse, SchoolUpdate

router = APIRouter(prefix="/schools", tags=["Schools"])


@router.get("", response_model=list[SchoolResponse])
def list_schools(db: Session = Depends(get_db)):
    return db.scalars(select(School).order_by(School.id)).all()


@router.post("", response_model=SchoolResponse, status_code=status.HTTP_201_CREATED)
def create_school(payload: SchoolCreate, db: Session = Depends(get_db)):
    now = now_utc()
    school = School(created_at=now, updated_at=now, **payload.model_dump())
    db.add(school)
    commit_or_conflict(db)
    db.refresh(school)
    return school


@router.get("/{school_id}", response_model=SchoolResponse)
def get_school(school_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, School, school_id)


@router.patch("/{school_id}", response_model=SchoolResponse)
def update_school(school_id: int, payload: SchoolUpdate, db: Session = Depends(get_db)):
    school = get_or_404(db, School, school_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(school, key, value)
    school.updated_at = now_utc()
    commit_or_conflict(db)
    db.refresh(school)
    return school


@router.delete("/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_school(school_id: int, db: Session = Depends(get_db)):
    school = get_or_404(db, School, school_id)
    db.delete(school)
    commit_or_conflict(db)
