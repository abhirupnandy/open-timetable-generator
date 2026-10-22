from __future__ import annotations

from types import SimpleNamespace

from app.db.models.subject import SubjectType
from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.schedule import Timetable
from app.optimisation.theory_sessions import calculate_theory_sessions_penalty


def make_placement(
    *,
    session_id: int,
    faculty_id: int,
    subject_id: int,
    subject_type: SubjectType,
    day: Day,
    start_period: int,
) -> SessionPlacement:
    session = SimpleNamespace(
        id=session_id,
        faculty_id=faculty_id,
        subject_id=subject_id,
        subject_type=subject_type,
        duration_periods=1,
    )

    return SessionPlacement(
        session=session,
        day=day,
        start_period=start_period,
    )


def make_timetable(placements: list[SessionPlacement]) -> Timetable:
    return Timetable(
        placements=tuple(placements),
    )


def test_two_lecture_sessions_in_a_day_have_no_penalty() -> None:
    timetable = make_timetable(
        [
            make_placement(
                session_id=1,
                faculty_id=1,
                subject_id=1,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id=2,
                faculty_id=1,
                subject_id=2,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=3,
            ),
        ]
    )

    assert calculate_theory_sessions_penalty(timetable) == 0


def test_three_lecture_sessions_in_a_day_have_one_penalty() -> None:
    timetable = make_timetable(
        [
            make_placement(
                session_id=1,
                faculty_id=1,
                subject_id=1,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id=2,
                faculty_id=1,
                subject_id=2,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=3,
            ),
            make_placement(
                session_id=3,
                faculty_id=1,
                subject_id=3,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=5,
            ),
        ]
    )

    assert calculate_theory_sessions_penalty(timetable) == 1


def test_four_lecture_sessions_in_a_day_have_two_penalty() -> None:
    timetable = make_timetable(
        [
            make_placement(
                session_id=index,
                faculty_id=1,
                subject_id=index,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=index,
            )
            for index in range(1, 5)
        ]
    )

    assert calculate_theory_sessions_penalty(timetable) == 2


def test_labs_do_not_count_as_theory_sessions() -> None:
    timetable = make_timetable(
        [
            make_placement(
                session_id=1,
                faculty_id=1,
                subject_id=1,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id=2,
                faculty_id=1,
                subject_id=2,
                subject_type=SubjectType.LAB,
                day=Day.MONDAY,
                start_period=3,
            ),
            make_placement(
                session_id=3,
                faculty_id=1,
                subject_id=3,
                subject_type=SubjectType.LAB,
                day=Day.MONDAY,
                start_period=5,
            ),
        ]
    )

    assert calculate_theory_sessions_penalty(timetable) == 0


def test_tutorials_do_not_count_as_theory_sessions() -> None:
    timetable = make_timetable(
        [
            make_placement(
                session_id=1,
                faculty_id=1,
                subject_id=1,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id=2,
                faculty_id=1,
                subject_id=2,
                subject_type=SubjectType.TUTORIAL,
                day=Day.MONDAY,
                start_period=3,
            ),
            make_placement(
                session_id=3,
                faculty_id=1,
                subject_id=3,
                subject_type=SubjectType.TUTORIAL,
                day=Day.MONDAY,
                start_period=5,
            ),
        ]
    )

    assert calculate_theory_sessions_penalty(timetable) == 0


def test_theory_sessions_are_counted_separately_by_faculty_and_day() -> None:
    timetable = make_timetable(
        [
            make_placement(
                session_id=1,
                faculty_id=1,
                subject_id=1,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id=2,
                faculty_id=1,
                subject_id=2,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=2,
            ),
            make_placement(
                session_id=3,
                faculty_id=1,
                subject_id=3,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=3,
            ),
            make_placement(
                session_id=4,
                faculty_id=2,
                subject_id=4,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id=5,
                faculty_id=2,
                subject_id=5,
                subject_type=SubjectType.LECTURE,
                day=Day.MONDAY,
                start_period=2,
            ),
        ]
    )

    assert calculate_theory_sessions_penalty(timetable) == 1