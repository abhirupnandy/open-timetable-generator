from __future__ import annotations

from dataclasses import dataclass

from app.db.models import SubjectType
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
    subject_type: SubjectType | None = None
    allow_across_lunch: bool = False


@dataclass(frozen=True)
class GroupBlockedSlot:
    """A period in which an academic group (and all its descendants) is unavailable."""

    academic_group_id: int
    day: Day
    period: int
    label: str = ""


@dataclass(frozen=True)
class SessionLock:
    """Pins one session to a day/start period and, optionally, a room."""

    session_id: str
    day: Day
    start_period: int
    room_id: int | None = None


@dataclass(frozen=True)
class PreviousPlacement:
    """Where a session was placed in a previous timetable (for stability)."""

    day: Day
    start_period: int
    room_id: int | None = None


@dataclass(frozen=True)
class TimetableInput:
    days: tuple[Day, ...]
    periods_per_day: int
    sessions: tuple[SchedulingSession, ...]
    academic_group_capacities: dict[int, int] | None = None
    academic_group_parent_ids: dict[int, int | None] | None = None
    faculty_designations: dict[int, str] | None = None
    faculty_time_preferences: dict[int, str] | None = None
    faculty_availability: dict[int, ResourceAvailability] | None = None
    room_availability: dict[int, ResourceAvailability] | None = None
    rooms: tuple[SchedulingRoom, ...] | None = None
    # Calendar. ``period_times`` maps period number -> (start, end) minutes;
    # ``None`` falls back to the default calendar in ``app.domain.calendar``.
    period_times: dict[int, tuple[int, int]] | None = None
    lunch_after_period: int | None = None
    blocked_slots: tuple[TimeSlot, ...] = ()
    group_blocked_slots: tuple[GroupBlockedSlot, ...] = ()
    session_locks: tuple[SessionLock, ...] = ()
    faculty_preferred_day_off: dict[int, Day] | None = None
    previous_placements: dict[str, PreviousPlacement] | None = None