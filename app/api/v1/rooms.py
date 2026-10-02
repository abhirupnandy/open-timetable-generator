from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1._common import commit_or_conflict, get_or_404, now_utc, require_exists
from app.db.models import Room, School
from app.db.session import get_db
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.get("", response_model=list[RoomResponse])
def list_rooms(school_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Room).order_by(Room.id)
    if school_id is not None:
        stmt = stmt.where(Room.school_id == school_id)
    return db.scalars(stmt).all()


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, db: Session = Depends(get_db)):
    require_exists(db, School, payload.school_id, "school_id")
    now = now_utc()
    room = Room(created_at=now, updated_at=now, **payload.model_dump())
    db.add(room)
    commit_or_conflict(db)
    db.refresh(room)
    return room


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Room, room_id)


@router.patch("/{room_id}", response_model=RoomResponse)
def update_room(room_id: int, payload: RoomUpdate, db: Session = Depends(get_db)):
    room = get_or_404(db, Room, room_id)
    values = payload.model_dump(exclude_unset=True)
    if "school_id" in values:
        require_exists(db, School, values["school_id"], "school_id")
    for key, value in values.items():
        setattr(room, key, value)
    room.updated_at = now_utc()
    commit_or_conflict(db)
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = get_or_404(db, Room, room_id)
    db.delete(room)
    commit_or_conflict(db)
