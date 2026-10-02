from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RoomType(StrEnum):
    LECTURE_HALL = "LECTURE_HALL"
    COMPUTER_LAB = "COMPUTER_LAB"
    SPECIAL_LAB = "SPECIAL_LAB"
    CLASSROOM = "CLASSROOM"


@dataclass(frozen=True)
class SchedulingRoom:
    id: int
    room_type: RoomType
    capacity: int
    is_shared: bool = False

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise ValueError("id must be greater than 0")

        if self.capacity <= 0:
            raise ValueError("capacity must be greater than 0")