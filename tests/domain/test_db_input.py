from sqlalchemy import select

from app.db.models import TeachingAssignment
from app.db.session import SessionLocal
from app.domain.db_input import build_timetable_input_from_db


def test_build_timetable_input_from_seeded_database() -> None:
    with SessionLocal() as db:
        timetable_input = build_timetable_input_from_db(db)

        assignments = tuple(
            db.scalars(
                select(TeachingAssignment).where(
                    TeachingAssignment.is_active.is_(True)
                )
            ).all()
        )

    assert len(assignments) == 80
    assert len(timetable_input.sessions) == 173
    assert len(timetable_input.rooms or ()) == 16
    assert len(timetable_input.academic_group_capacities or {}) == 48

    assert all(
        session.duration_periods > 0
        for session in timetable_input.sessions
    )

    assert all(
        session.faculty_id > 0
        for session in timetable_input.sessions
    )

    assert all(
        session.academic_group_id > 0
        for session in timetable_input.sessions
    )

    assert timetable_input.faculty_designations is not None
    assert len(timetable_input.faculty_designations) > 0

    assert all(
        faculty_id > 0
        for faculty_id in timetable_input.faculty_designations
    )

    assert all(
        designation
        in {
            "PROFESSOR",
            "ASSOCIATE_PROFESSOR",
            "ASSISTANT_PROFESSOR",
            "PHD_SCHOLAR",
        }
        for designation in timetable_input.faculty_designations.values()
    )