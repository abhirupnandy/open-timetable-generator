from dataclasses import dataclass

from app.domain.placement import SessionPlacement
from app.domain.room import SchedulingRoom


@dataclass(frozen=True)
class RoomAssignment:
    placement: SessionPlacement
    room: SchedulingRoom