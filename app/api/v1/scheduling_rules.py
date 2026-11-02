"""CRUD for constraint inputs: unavailability, group blocked slots, session locks."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1._common import commit_or_conflict, get_or_404, now_utc, require_exists
from app.db.models import (
    AcademicGroup,
    Faculty,
    GroupBlockedSlot,
    ResourceType,
    Room,
    SessionLock,
    TeachingAssignment,
    Unavailability,
)
from app.db.session import get_db
from app.schemas.scheduling_rules import (
    GroupBlockedSlotCreate,
    GroupBlockedSlotResponse,
    GroupBlockedSlotUpdate,
    SessionLockCreate,
    SessionLockResponse,
    SessionLockUpdate,
    UnavailabilityCreate,
    UnavailabilityResponse,
    UnavailabilityUpdate,
)

unavailability_router = APIRouter(prefix="/unavailability", tags=["Unavailability"])
group_blocks_router = APIRouter(prefix="/group-blocked-slots", tags=["Group Blocked Slots"])
session_locks_router = APIRouter(prefix="/session-locks", tags=["Session Locks"])


def _apply_update(db: Session, obj, values: dict) -> None:
    for key, value in values.items():
        setattr(obj, key, value)
    obj.updated_at = now_utc()
    commit_or_conflict(db)
    db.refresh(obj)


def _create(db: Session, model, payload) -> object:
    now = now_utc()
    obj = model(created_at=now, updated_at=now, **payload.model_dump())
    db.add(obj)
    commit_or_conflict(db)
    db.refresh(obj)
    return obj


# ---------------------------------------------------------------------------
# Unavailability
# ---------------------------------------------------------------------------


def _require_resource(db: Session, resource_type: ResourceType, resource_id: int) -> None:
    model = Faculty if resource_type == ResourceType.FACULTY else Room
    require_exists(db, model, resource_id, "resource_id")


@unavailability_router.get("", response_model=list[UnavailabilityResponse])
def list_unavailability(
    resource_type: ResourceType | None = None,
    resource_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Unavailability).order_by(Unavailability.id)
    if resource_type is not None:
        stmt = stmt.where(Unavailability.resource_type == resource_type)
    if resource_id is not None:
        stmt = stmt.where(Unavailability.resource_id == resource_id)
    return db.scalars(stmt).all()


@unavailability_router.post(
    "", response_model=UnavailabilityResponse, status_code=status.HTTP_201_CREATED
)
def create_unavailability(payload: UnavailabilityCreate, db: Session = Depends(get_db)):
    _require_resource(db, payload.resource_type, payload.resource_id)
    return _create(db, Unavailability, payload)


@unavailability_router.get("/{item_id}", response_model=UnavailabilityResponse)
def get_unavailability(item_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Unavailability, item_id)


@unavailability_router.patch("/{item_id}", response_model=UnavailabilityResponse)
def update_unavailability(
    item_id: int, payload: UnavailabilityUpdate, db: Session = Depends(get_db)
):
    item = get_or_404(db, Unavailability, item_id)
    values = payload.model_dump(exclude_unset=True)
    start = values.get("start_period", item.start_period)
    end = values.get("end_period", item.end_period)
    if end < start:
        raise HTTPException(
            status_code=422,
            detail="end_period must be greater than or equal to start_period",
        )
    _apply_update(db, item, values)
    return item


@unavailability_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unavailability(item_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Unavailability, item_id))
    commit_or_conflict(db)


# ---------------------------------------------------------------------------
# Group blocked slots
# ---------------------------------------------------------------------------


@group_blocks_router.get("", response_model=list[GroupBlockedSlotResponse])
def list_group_blocked_slots(
    academic_group_id: int | None = None, db: Session = Depends(get_db)
):
    stmt = select(GroupBlockedSlot).order_by(GroupBlockedSlot.id)
    if academic_group_id is not None:
        stmt = stmt.where(GroupBlockedSlot.academic_group_id == academic_group_id)
    return db.scalars(stmt).all()


@group_blocks_router.post(
    "", response_model=GroupBlockedSlotResponse, status_code=status.HTTP_201_CREATED
)
def create_group_blocked_slot(payload: GroupBlockedSlotCreate, db: Session = Depends(get_db)):
    require_exists(db, AcademicGroup, payload.academic_group_id, "academic_group_id")
    return _create(db, GroupBlockedSlot, payload)


@group_blocks_router.get("/{item_id}", response_model=GroupBlockedSlotResponse)
def get_group_blocked_slot(item_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, GroupBlockedSlot, item_id)


@group_blocks_router.patch("/{item_id}", response_model=GroupBlockedSlotResponse)
def update_group_blocked_slot(
    item_id: int, payload: GroupBlockedSlotUpdate, db: Session = Depends(get_db)
):
    item = get_or_404(db, GroupBlockedSlot, item_id)
    _apply_update(db, item, payload.model_dump(exclude_unset=True))
    return item


@group_blocks_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group_blocked_slot(item_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, GroupBlockedSlot, item_id))
    commit_or_conflict(db)


# ---------------------------------------------------------------------------
# Session locks
# ---------------------------------------------------------------------------


def _check_lock(
    db: Session,
    assignment: TeachingAssignment,
    session_number: int,
    start_period: int,
    room_id: int | None,
) -> None:
    if session_number > assignment.sessions_per_week:
        raise HTTPException(
            status_code=422,
            detail=(
                f"session_number {session_number} exceeds the assignment's "
                f"{assignment.sessions_per_week} sessions per week"
            ),
        )
    if start_period < 1:
        raise HTTPException(status_code=422, detail="start_period must be at least 1")
    if room_id is not None:
        require_exists(db, Room, room_id, "room_id")


@session_locks_router.get("", response_model=list[SessionLockResponse])
def list_session_locks(
    teaching_assignment_id: int | None = None, db: Session = Depends(get_db)
):
    stmt = select(SessionLock).order_by(SessionLock.id)
    if teaching_assignment_id is not None:
        stmt = stmt.where(SessionLock.teaching_assignment_id == teaching_assignment_id)
    return db.scalars(stmt).all()


@session_locks_router.post(
    "", response_model=SessionLockResponse, status_code=status.HTTP_201_CREATED
)
def create_session_lock(payload: SessionLockCreate, db: Session = Depends(get_db)):
    assignment = get_or_404(db, TeachingAssignment, payload.teaching_assignment_id)
    _check_lock(db, assignment, payload.session_number, payload.start_period, payload.room_id)
    return _create(db, SessionLock, payload)


@session_locks_router.get("/{item_id}", response_model=SessionLockResponse)
def get_session_lock(item_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, SessionLock, item_id)


@session_locks_router.patch("/{item_id}", response_model=SessionLockResponse)
def update_session_lock(item_id: int, payload: SessionLockUpdate, db: Session = Depends(get_db)):
    item = get_or_404(db, SessionLock, item_id)
    values = payload.model_dump(exclude_unset=True)
    assignment = get_or_404(db, TeachingAssignment, item.teaching_assignment_id)
    _check_lock(
        db,
        assignment,
        item.session_number,
        values.get("start_period", item.start_period),
        values.get("room_id", item.room_id),
    )
    _apply_update(db, item, values)
    return item


@session_locks_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_lock(item_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, SessionLock, item_id))
    commit_or_conflict(db)
