from __future__ import annotations

from app.domain.placement import SessionPlacement
from app.domain.room import SchedulingRoom
from app.domain.room_candidate_domains import build_room_candidate_domain
from app.domain.scheduling_candidate import SchedulingCandidate
from app.domain.timetable import TimetableInput


def build_scheduling_candidates(
    placement: SessionPlacement,
    rooms: tuple[SchedulingRoom, ...],
    timetable_input: TimetableInput,
) -> tuple[SchedulingCandidate, ...]:
    """Build all valid placement-and-room candidates for one placement."""

    mode = placement.session.mode

    if mode == "ONLINE":
        return (
            SchedulingCandidate(
                placement=placement,
                room=None,
            ),
        )

    candidate_rooms = build_room_candidate_domain(
        placement,
        rooms,
        timetable_input,
    )

    physical_candidates = tuple(
        SchedulingCandidate(
            placement=placement,
            room=room,
        )
        for room in candidate_rooms
    )

    if mode == "EITHER":
        return (
            SchedulingCandidate(
                placement=placement,
                room=None,
            ),
            *physical_candidates,
        )

    return physical_candidates