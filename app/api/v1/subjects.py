from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1._common import commit_or_conflict, get_or_404, now_utc
from app.db.models import Subject
from app.db.session import get_db
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get("", response_model=list[SubjectResponse])
def list_subjects(db: Session = Depends(get_db)):
    return db.scalars(select(Subject).order_by(Subject.id)).all()


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    now = now_utc()
    subject = Subject(created_at=now, updated_at=now, **payload.model_dump())
    db.add(subject)
    commit_or_conflict(db)
    db.refresh(subject)
    return subject


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Subject, subject_id)


@router.patch("/{subject_id}", response_model=SubjectResponse)
def update_subject(subject_id: int, payload: SubjectUpdate, db: Session = Depends(get_db)):
    subject = get_or_404(db, Subject, subject_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(subject, key, value)
    subject.updated_at = now_utc()
    commit_or_conflict(db)
    db.refresh(subject)
    return subject


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = get_or_404(db, Subject, subject_id)
    db.delete(subject)
    commit_or_conflict(db)
