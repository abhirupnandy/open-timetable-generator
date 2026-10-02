from __future__ import annotations

from app.domain.timetable import SchedulingSession


def expand_teaching_assignment(
    *,
    teaching_assignment_id: int,
    subject_id: int,
    course_id: int,
    academic_group_id: int,
    faculty_id: int,
    sessions_per_week: int,
    duration_periods: int,
    mode: str,
    required_room_type: str | None,
) -> tuple[SchedulingSession, ...]:
    """Expand one teaching assignment into individual schedulable sessions."""

    if sessions_per_week <= 0:
        raise ValueError("sessions_per_week must be greater than 0")

    if duration_periods <= 0:
        raise ValueError("duration_periods must be greater than 0")

    return tuple(
        SchedulingSession(
            id=f"assignment:{teaching_assignment_id}:session:{session_number}",
            teaching_assignment_id=teaching_assignment_id,
            subject_id=subject_id,
            course_id=course_id,
            academic_group_id=academic_group_id,
            faculty_id=faculty_id,
            duration_periods=duration_periods,
            mode=mode,
            required_room_type=required_room_type,
            session_number=session_number,
        )
        for session_number in range(1, sessions_per_week + 1)
    )