from __future__ import annotations

from collections.abc import Iterable

from app.domain.placement import SessionPlacement
from app.domain.room import SchedulingRoom
from app.domain.room_placement import is_room_available_for_placement
from app.domain.room_suitability import is_room_suitable
from app.domain.timetable import SchedulingSession, TimetableInput


def candidate_rooms(
    session: SchedulingSession,
    rooms: Iterable[SchedulingRoom],
    timetable_input: TimetableInput,
) -> tuple[SchedulingRoom, ...]:
    """Return rooms that are suitable for a scheduling session."""

    return tuple(
        room
        for room in rooms
        if is_room_suitable(
            session,
            room,
            timetable_input,
        )
    )


def candidate_rooms_for_placement(
    placement: SessionPlacement,
    rooms: tuple[SchedulingRoom, ...],
    timetable_input: TimetableInput,
) -> tuple[SchedulingRoom, ...]:
    """Return suitable and available rooms for a session placement."""

    suitable_rooms = candidate_rooms(
        placement.session,
        rooms,
        timetable_input,
    )

    room_availability = timetable_input.room_availability

    return tuple(
        room
        for room in suitable_rooms
        if is_room_available_for_placement(
            room,
            placement,
            (
                room_availability.get(room.id)
                if room_availability is not None
                else None
            ),
        )
    )