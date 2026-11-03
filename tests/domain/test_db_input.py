from sqlalchemy import select

from app.db.models import TeachingAssignment
from app.domain.db_input import build_timetable_input_from_db


def test_build_timetable_input_from_seeded_database(seeded_session_factory) -> None:
    with seeded_session_factory() as db:
        timetable_input = build_timetable_input_from_db(db)
        assignments = tuple(
            db.scalars(
                select(TeachingAssignment).where(TeachingAssignment.is_active.is_(True))
            ).all()
        )

    assert len(assignments) == 80
    assert len(timetable_input.sessions) == 173
    assert len(timetable_input.rooms or ()) == 16
    assert len(timetable_input.academic_group_capacities or {}) == 48
    assert all(session.duration_periods > 0 for session in timetable_input.sessions)
    assert timetable_input.faculty_designations is not None
    assert set(timetable_input.faculty_designations.values()) <= {
        "PROFESSOR",
        "ASSOCIATE_PROFESSOR",
        "ASSISTANT_PROFESSOR",
        "PHD_SCHOLAR",
    }
