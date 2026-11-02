from __future__ import annotations

from collections.abc import Iterable

from app.core.timetable_config import CalendarConfig, load_timetable_config
from app.db.models import TeachingAssignment
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import SchedulingRoom
from app.domain.session_expansion import expand_teaching_assignment
from app.domain.timetable import (
    Day,
    GroupBlockedSlot,
    PreviousPlacement,
    SessionLock,
    TimeSlot,
    TimetableInput,
)


def build_timetable_input(
    teaching_assignments: Iterable[TeachingAssignment],
    *,
    days: tuple[Day, ...] | None = None,
    periods_per_day: int | None = None,
    calendar: CalendarConfig | None = None,
    academic_group_capacities: dict[int, int] | None = None,
    academic_group_parent_ids: dict[int, int | None] | None = None,
    faculty_designations: dict[int, str] | None = None,
    faculty_time_preferences: dict[int, str] | None = None,
    faculty_availability: dict[int, ResourceAvailability] | None = None,
    room_availability: dict[int, ResourceAvailability] | None = None,
    rooms: tuple[SchedulingRoom, ...] | None = None,
    group_blocked_slots: tuple[GroupBlockedSlot, ...] = (),
    session_locks: tuple[SessionLock, ...] = (),
    faculty_preferred_day_off: dict[int, Day] | None = None,
    previous_placements: dict[str, PreviousPlacement] | None = None,
) -> TimetableInput:
    """Build the solver-independent timetable input from database assignments.

    The calendar (days, periods, period times, lunch position and global
    blocked slots) comes from ``calendar``, defaulting to the one in
    ``config/timetable.toml``. ``days`` / ``periods_per_day`` override it.
    """

    if calendar is None:
        calendar = load_timetable_config().calendar

    if days is None:
        days = tuple(Day(day) for day in calendar.days)

    if periods_per_day is None:
        periods_per_day = calendar.periods_per_day

    if not days:
        raise ValueError("At least one timetable day is required")

    if periods_per_day <= 0:
        raise ValueError("periods_per_day must be greater than 0")

    calendar_matches = periods_per_day == calendar.periods_per_day

    lunch_after_period = calendar.lunch_after_period
    if lunch_after_period is not None and lunch_after_period >= periods_per_day:
        lunch_after_period = None

    blocked_slots = tuple(
        TimeSlot(day=Day(slot.day), period=slot.period)
        for slot in calendar.blocked_slots
        if Day(slot.day) in days and slot.period <= periods_per_day
    )

    sessions = tuple(
        session
        for assignment in teaching_assignments
        if assignment.is_active
        for session in expand_teaching_assignment(
            teaching_assignment_id=assignment.id,
            subject_id=assignment.subject_id,
            subject_type=(
                assignment.subject.subject_type if assignment.subject is not None else None
            ),
            course_id=assignment.course_id,
            academic_group_id=assignment.academic_group_id,
            faculty_id=assignment.faculty_id,
            sessions_per_week=assignment.sessions_per_week,
            duration_periods=assignment.duration_periods,
            mode=assignment.mode.value,
            required_room_type=assignment.required_room_type,
            allow_across_lunch=bool(getattr(assignment, "allow_across_lunch", False)),
        )
    )

    return TimetableInput(
        days=days,
        periods_per_day=periods_per_day,
        sessions=sessions,
        academic_group_capacities=academic_group_capacities,
        academic_group_parent_ids=academic_group_parent_ids,
        faculty_designations=faculty_designations,
        faculty_time_preferences=faculty_time_preferences,
        faculty_availability=faculty_availability,
        room_availability=room_availability,
        rooms=rooms,
        period_times=calendar.period_times if calendar_matches else None,
        lunch_after_period=lunch_after_period,
        blocked_slots=blocked_slots,
        group_blocked_slots=group_blocked_slots,
        session_locks=session_locks,
        faculty_preferred_day_off=faculty_preferred_day_off,
        previous_placements=previous_placements,
    )
