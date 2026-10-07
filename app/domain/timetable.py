from __future__ import annotations

from dataclasses import dataclass

from app.domain.calendar import Day
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import SchedulingRoom


@dataclass(frozen=True)
class TimeSlot:
    day: Day
    period: int


@dataclass(frozen=True)
class SchedulingSession:
    id: str
    teaching_assignment_id: int
    subject_id: int
    course_id: int
    academic_group_id: int
    faculty_id: int
    duration_periods: int
    mode: str
    required_room_type: str | None
    session_number: int


@dataclass(frozen=True)
class TimetableInput:
    days: tuple[Day, ...]
    periods_per_day: int
    sessions: tuple[SchedulingSession, ...]
    academic_group_capacities: dict[int, int] | None = None
    academic_group_parent_ids: dict[int, int | None] | None = None
    faculty_availability: dict[int, ResourceAvailability] | None = None
    room_availability: dict[int, ResourceAvailability] | None = None
    rooms: tuple[SchedulingRoom, ...] | None = None