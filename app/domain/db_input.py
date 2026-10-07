from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AcademicGroup, Room, TeachingAssignment
from app.domain.input_builder import build_timetable_input
from app.domain.room import SchedulingRoom
from app.domain.timetable import TimetableInput


def build_timetable_input_from_db(db: Session) -> TimetableInput:
    teaching_assignments = tuple(
        db.scalars(
            select(TeachingAssignment).where(
                TeachingAssignment.is_active.is_(True)
            )
        ).all()
    )

    groups = tuple(
        db.scalars(
            select(AcademicGroup).where(
                AcademicGroup.is_active.is_(True)
            )
        ).all()
    )

    rooms = tuple(
        db.scalars(
            select(Room).where(
                Room.is_active.is_(True)
            )
        ).all()
    )

    academic_group_capacities = {
        group.id: group.capacity
        for group in groups
        if group.capacity is not None
    }

    academic_group_parent_ids = {
        group.id: group.parent_group_id
        for group in groups
    }

    scheduling_rooms = tuple(
        SchedulingRoom(
            id=room.id,
            room_type=room.room_type,
            capacity=room.capacity,
            is_shared=room.is_shared,
        )
        for room in rooms
    )

    return build_timetable_input(
        teaching_assignments,
        academic_group_capacities=academic_group_capacities,
        academic_group_parent_ids=academic_group_parent_ids,
        rooms=scheduling_rooms,
    )