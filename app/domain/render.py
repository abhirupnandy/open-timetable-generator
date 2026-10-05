from __future__ import annotations

from collections.abc import Mapping

from app.domain.calendar import Day
from app.domain.schedule import Timetable


def render_timetable(
    timetable: Timetable,
    *,
    subject_names: Mapping[int, str] | None = None,
    group_names: Mapping[int, str] | None = None,
    faculty_names: Mapping[int, str] | None = None,
    room_names: Mapping[int, str] | None = None,
) -> str:
    """Render a timetable as a human-readable text table."""

    subject_names = subject_names or {}
    group_names = group_names or {}
    faculty_names = faculty_names or {}
    room_names = room_names or {}

    room_by_session_id = {
        assignment.placement.session.id: assignment.room
        for assignment in timetable.room_assignments
    }

    day_order = {day: index for index, day in enumerate(Day)}

    placements = sorted(
        timetable.placements,
        key=lambda placement: (
            day_order[placement.day],
            placement.start_period,
            placement.session.id,
        ),
    )

    if not placements:
        return "Timetable is empty."

    lines: list[str] = []
    current_day = None

    for placement in placements:
        if placement.day != current_day:
            if lines:
                lines.append("")

            lines.append(placement.day.value)
            lines.append("-" * len(placement.day.value))
            current_day = placement.day

        session = placement.session
        room = room_by_session_id.get(session.id)

        subject_label = subject_names.get(
            session.subject_id,
            f"Subject {session.subject_id}",
        )
        group_label = group_names.get(
            session.academic_group_id,
            f"Group {session.academic_group_id}",
        )
        faculty_label = faculty_names.get(
            session.faculty_id,
            f"Faculty {session.faculty_id}",
        )

        room_label = (
            "ONLINE"
            if room is None
            else room_names.get(room.id, f"Room {room.id}")
        )

        period_label = (
            str(placement.start_period)
            if placement.start_period == placement.end_period
            else f"{placement.start_period}-{placement.end_period}"
        )

        lines.append(
            f"P{period_label:<5} "
            f"{subject_label:<28} "
            f"{group_label:<20} "
            f"{faculty_label:<24} "
            f"{room_label}"
        )

    return "\n".join(lines)