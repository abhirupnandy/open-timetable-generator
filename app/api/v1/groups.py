from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1._common import commit_or_conflict, get_or_404, now_utc, require_exists
from app.db.models import AcademicGroup, Course
from app.db.session import get_db
from app.schemas.academic_group import (
    AcademicGroupCreate,
    AcademicGroupResponse,
    AcademicGroupUpdate,
)

router = APIRouter(prefix="/groups", tags=["Academic Groups"])


@router.get("", response_model=list[AcademicGroupResponse])
def list_groups(course_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(AcademicGroup).order_by(AcademicGroup.id)
    if course_id is not None:
        stmt = stmt.where(AcademicGroup.course_id == course_id)
    return db.scalars(stmt).all()


@router.post("", response_model=AcademicGroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(payload: AcademicGroupCreate, db: Session = Depends(get_db)):
    require_exists(db, Course, payload.course_id, "course_id")
    if payload.parent_group_id is not None:
        require_exists(db, AcademicGroup, payload.parent_group_id, "parent_group_id")
    now = now_utc()
    group = AcademicGroup(created_at=now, updated_at=now, **payload.model_dump())
    db.add(group)
    commit_or_conflict(db)
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=AcademicGroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, AcademicGroup, group_id)


@router.patch("/{group_id}", response_model=AcademicGroupResponse)
def update_group(group_id: int, payload: AcademicGroupUpdate, db: Session = Depends(get_db)):
    group = get_or_404(db, AcademicGroup, group_id)
    values = payload.model_dump(exclude_unset=True)
    if "course_id" in values:
        require_exists(db, Course, values["course_id"], "course_id")
    if "parent_group_id" in values and values["parent_group_id"] is not None:
        if values["parent_group_id"] == group_id:
            raise HTTPException(status_code=422, detail="A group cannot be its own parent")
        require_exists(db, AcademicGroup, values["parent_group_id"], "parent_group_id")
    for key, value in values.items():
        setattr(group, key, value)
    group.updated_at = now_utc()
    commit_or_conflict(db)
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = get_or_404(db, AcademicGroup, group_id)
    db.delete(group)
    commit_or_conflict(db)
