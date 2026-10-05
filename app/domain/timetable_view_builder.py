from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.db_render_data import load_render_metadata
from app.domain.schedule import Timetable
from app.domain.timetable_views import TimetableViewEntry


def build_timetable_view_entries(
    db: Session,
    timetable: Timetable,
) -> tuple[TimetableViewEntry, ...]:
    """Build human-readable entries from the canonical timetable."""

    (
        subject_names,
        group_metadata,
        faculty_names,
        room_names,
        course_metadata,
    ) = load_render_metadata(db)

    room_by_session_id = {
        assignment.placement.session.id: assignment.room.id
        for assignment in timetable.room_assignments
    }

    entries: list[TimetableViewEntry] = []

    for placement in timetable.placements:
        session = placement.session

        group_code, group_name = group_metadata[session.academic_group_id]
        course_code, course_name = course_metadata[session.course_id]

        room_id = room_by_session_id.get(session.id)

        entries.append(
            TimetableViewEntry(
                session_id=session.id,
                day=placement.day,
                start_period=placement.start_period,
                end_period=placement.end_period,
                subject_name=subject_names[session.subject_id],
                course_code=course_code,
                course_name=course_name,
                academic_group_name=group_name,
                academic_group_code=group_code,
                faculty_name=faculty_names[session.faculty_id],
                room_name=room_names[room_id] if room_id is not None else None,
            )
        )

    return tuple(entries)