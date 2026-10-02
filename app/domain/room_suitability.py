from __future__ import annotations

from app.domain.room import SchedulingRoom
from app.domain.timetable import SchedulingSession, TimetableInput


def is_room_suitable(
    session: SchedulingSession,
    room: SchedulingRoom,
    timetable_input: TimetableInput,
) -> bool:
    """Return whether a room satisfies the session's room requirements."""

    if session.mode == "ONLINE":
        return False

    if session.required_room_type is not None:
        if room.room_type.value != session.required_room_type:
            return False

    if timetable_input.academic_group_capacities is None:
        return True

    group_capacity = timetable_input.academic_group_capacities.get(
        session.academic_group_id
    )

    if group_capacity is None:
        return False

    return room.capacity >= group_capacity