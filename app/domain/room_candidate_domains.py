from __future__ import annotations

from app.domain.placement import SessionPlacement
from app.domain.room import SchedulingRoom
from app.domain.room_candidates import candidate_rooms_for_placement
from app.domain.timetable import TimetableInput


class EmptyRoomCandidateDomainError(ValueError):
    """Raised when a session placement has no valid candidate room."""

    def __init__(self, session_placement: SessionPlacement) -> None:
        super().__init__(
            "Session placement has no valid candidate rooms: "
            f"{session_placement.session.id}"
        )
        self.session_placement = session_placement


def build_room_candidate_domain(
    placement: SessionPlacement,
    rooms: tuple[SchedulingRoom, ...],
    timetable_input: TimetableInput,
) -> tuple[SchedulingRoom, ...]:
    """Build the valid room domain for one session placement."""

    rooms_for_placement = candidate_rooms_for_placement(
        placement,
        rooms,
        timetable_input,
    )

    if not rooms_for_placement:
        raise EmptyRoomCandidateDomainError(placement)

    return rooms_for_placement