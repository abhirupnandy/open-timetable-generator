from sqlalchemy import select

from app.db.models import TeachingAssignment
from app.db.session import SessionLocal
from app.domain.db_input import build_timetable_input_from_db
from app.domain.problem import SchedulingProblem
from app.domain.timetable_view_builder import build_timetable_view_entries
from app.optimisation.solver import solve


def test_seeded_database_produces_timetable() -> None:
    with SessionLocal() as db:
        teaching_assignments = tuple(
            db.scalars(
                select(TeachingAssignment).where(
                    TeachingAssignment.is_active.is_(True)
                )
            ).all()
        )

        timetable_input = build_timetable_input_from_db(db)

    problem = SchedulingProblem(timetable_input=timetable_input)

    result = solve(problem)

    assert len(teaching_assignments) == 50
    assert len(timetable_input.sessions) == 99
    assert len(result.timetable.placements) == 99

    session_ids = {
        placement.session.id
        for placement in result.timetable.placements
    }

    assert len(session_ids) == 99



def test_seeded_timetable_builds_view_entries() -> None:
    with SessionLocal() as db:
        timetable_input = build_timetable_input_from_db(db)

        problem = SchedulingProblem(timetable_input=timetable_input)
        result = solve(problem)

        entries = build_timetable_view_entries(
            db,
            result.timetable,
        )

    assert len(entries) == 99

    session_ids = {
        entry.session_id
        for entry in entries
    }

    assert len(session_ids) == 99

    for entry in entries:
        assert entry.subject_name
        assert entry.course_code
        assert entry.course_name
        assert entry.academic_group_code
        assert entry.academic_group_name
        assert entry.faculty_name
        assert entry.start_period > 0
        assert entry.end_period >= entry.start_period