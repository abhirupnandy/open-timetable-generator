from __future__ import annotations

from collections.abc import Iterable

from app.db.models import TeachingAssignment
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import SchedulingRoom
from app.domain.session_expansion import expand_teaching_assignment
from app.domain.timetable import Day, TimetableInput

DEFAULT_DAYS: tuple[Day, ...] = (
    Day.MONDAY,
    Day.TUESDAY,
    Day.WEDNESDAY,
    Day.THURSDAY,
    Day.FRIDAY,
)

DEFAULT_PERIODS_PER_DAY = 8


def build_timetable_input(
    teaching_assignments: Iterable[TeachingAssignment],
    *,
    days: tuple[Day, ...] = DEFAULT_DAYS,
    periods_per_day: int = DEFAULT_PERIODS_PER_DAY,
    academic_group_capacities: dict[int, int] | None = None,
    academic_group_parent_ids: dict[int, int | None] | None = None,
    faculty_availability: dict[int, ResourceAvailability] | None = None,
    room_availability: dict[int, ResourceAvailability] | None = None,
    rooms: tuple[SchedulingRoom, ...] | None = None,
) -> TimetableInput:
    """Build the solver-independent timetable input from database assignments."""

    if not days:
        raise ValueError("At least one timetable day is required")

    if periods_per_day <= 0:
        raise ValueError("periods_per_day must be greater than 0")

    sessions = tuple(
        session
        for assignment in teaching_assignments
        if assignment.is_active
        for session in expand_teaching_assignment(
            teaching_assignment_id=assignment.id,
            subject_id=assignment.subject_id,
            course_id=assignment.course_id,
            academic_group_id=assignment.academic_group_id,
            faculty_id=assignment.faculty_id,
            sessions_per_week=assignment.sessions_per_week,
            duration_periods=assignment.duration_periods,
            mode=assignment.mode.value,
            required_room_type=assignment.required_room_type,
        )
    )

    return TimetableInput(
        days=days,
        periods_per_day=periods_per_day,
        sessions=sessions,
        academic_group_capacities=academic_group_capacities,
        academic_group_parent_ids=academic_group_parent_ids,
        faculty_availability=faculty_availability,
        room_availability=room_availability,
        rooms=rooms,
    )