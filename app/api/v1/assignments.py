from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1._common import commit_or_conflict, get_or_404, now_utc, require_exists
from app.db.models import AcademicGroup, Course, Faculty, Subject, TeachingAssignment
from app.db.session import get_db
from app.schemas.teaching_assignment import (
    TeachingAssignmentCreate,
    TeachingAssignmentResponse,
    TeachingAssignmentUpdate,
)

router = APIRouter(prefix="/assignments", tags=["Teaching Assignments"])


@router.get("", response_model=list[TeachingAssignmentResponse])
def list_assignments(
    course_id: int | None = None,
    faculty_id: int | None = None,
    academic_group_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(TeachingAssignment).order_by(TeachingAssignment.id)

    if course_id is not None:
        stmt = stmt.where(TeachingAssignment.course_id == course_id)

    if faculty_id is not None:
        stmt = stmt.where(TeachingAssignment.faculty_id == faculty_id)

    if academic_group_id is not None:
        stmt = stmt.where(TeachingAssignment.academic_group_id == academic_group_id)

    return db.scalars(stmt).all()


@router.post(
    "",
    response_model=TeachingAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    payload: TeachingAssignmentCreate,
    db: Session = Depends(get_db),
):
    require_exists(db, Subject, payload.subject_id, "subject_id")
    require_exists(db, Course, payload.course_id, "course_id")
    require_exists(db, Faculty, payload.faculty_id, "faculty_id")

    academic_group = get_or_404(
        db,
        AcademicGroup,
        payload.academic_group_id,
    )

    if academic_group.course_id != payload.course_id:
        raise HTTPException(
            status_code=422,
            detail="Academic group must belong to the same course",
        )

    now = now_utc()

    assignment = TeachingAssignment(
        created_at=now,
        updated_at=now,
        **payload.model_dump(),
    )

    db.add(assignment)
    commit_or_conflict(db)
    db.refresh(assignment)

    return assignment


@router.get("/{assignment_id}", response_model=TeachingAssignmentResponse)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
):
    return get_or_404(db, TeachingAssignment, assignment_id)


@router.patch("/{assignment_id}", response_model=TeachingAssignmentResponse)
def update_assignment(
    assignment_id: int,
    payload: TeachingAssignmentUpdate,
    db: Session = Depends(get_db),
):
    assignment = get_or_404(db, TeachingAssignment, assignment_id)

    values = payload.model_dump(exclude_unset=True)

    checks = [
        ("subject_id", Subject),
        ("course_id", Course),
        ("academic_group_id", AcademicGroup),
        ("faculty_id", Faculty),
    ]

    for field, model in checks:
        if field in values:
            require_exists(db, model, values[field], field)

    # Determine the resulting course and academic group after the update.
    resulting_course_id = values.get("course_id", assignment.course_id)
    resulting_group_id = values.get(
        "academic_group_id",
        assignment.academic_group_id,
    )

    academic_group = get_or_404(
        db,
        AcademicGroup,
        resulting_group_id,
    )

    if academic_group.course_id != resulting_course_id:
        raise HTTPException(
            status_code=422,
            detail="Academic group must belong to the same course",
        )

    for key, value in values.items():
        setattr(assignment, key, value)

    assignment.updated_at = now_utc()

    commit_or_conflict(db)
    db.refresh(assignment)

    return assignment


@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
):
    assignment = get_or_404(db, TeachingAssignment, assignment_id)

    db.delete(assignment)
    commit_or_conflict(db)