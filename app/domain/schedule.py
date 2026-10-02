from __future__ import annotations

from dataclasses import dataclass

from app.domain.placement import SessionPlacement
from app.domain.room_assignment import RoomAssignment


@dataclass(frozen=True)
class Timetable:
    """A candidate timetable containing session placements and room assignments."""

    placements: tuple[SessionPlacement, ...]
    room_assignments: tuple[RoomAssignment, ...] = ()

    @classmethod
    def empty(cls) -> Timetable:
        """Create an empty timetable."""
        return cls(
            placements=(),
            room_assignments=(),
        )

    def add(self, placement: SessionPlacement) -> Timetable:
        """Return a new timetable with one additional placement."""
        return Timetable(
            placements=(*self.placements, placement),
            room_assignments=self.room_assignments,
        )

    def add_room_assignment(self, room_assignment: RoomAssignment) -> Timetable:
        """Return a new timetable with one additional room assignment."""
        return Timetable(
            placements=self.placements,
            room_assignments=(*self.room_assignments, room_assignment),
        )

    def __len__(self) -> int:
        return len(self.placements)