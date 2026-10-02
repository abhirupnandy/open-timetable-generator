from app.domain.conflicts import (
    academic_group_conflict,
    faculty_conflict,
)
from app.domain.placement import SessionPlacement
from app.domain.timetable import Day, SchedulingSession


def make_session(
    *,
    session_id: str,
    faculty_id: int = 40,
    academic_group_id: int = 30,
    duration_periods: int = 2,
) -> SchedulingSession:
    return SchedulingSession(
        id=session_id,
        teaching_assignment_id=1,
        subject_id=10,
        course_id=20,
        academic_group_id=academic_group_id,
        faculty_id=faculty_id,
        duration_periods=duration_periods,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )


def make_placement(
    *,
    session: SchedulingSession,
    day: Day = Day.MONDAY,
    start_period: int = 2,
) -> SessionPlacement:
    return SessionPlacement(
        session=session,
        day=day,
        start_period=start_period,
    )


def test_faculty_conflict_when_same_faculty_overlaps():
    first = make_placement(
        session=make_session(session_id="session-1", faculty_id=10),
    )

    second = make_placement(
        session=make_session(session_id="session-2", faculty_id=10),
        start_period=3,
    )

    assert faculty_conflict(first, second)


def test_no_faculty_conflict_when_faculty_differs():
    first = make_placement(
        session=make_session(session_id="session-1", faculty_id=10),
    )

    second = make_placement(
        session=make_session(session_id="session-2", faculty_id=20),
        start_period=3,
    )

    assert not faculty_conflict(first, second)


def test_no_faculty_conflict_when_times_do_not_overlap():
    first = make_placement(
        session=make_session(session_id="session-1", faculty_id=10),
    )

    second = make_placement(
        session=make_session(session_id="session-2", faculty_id=10),
        start_period=4,
    )

    assert not faculty_conflict(first, second)


def test_no_faculty_conflict_on_different_days():
    first = make_placement(
        session=make_session(session_id="session-1", faculty_id=10),
    )

    second = make_placement(
        session=make_session(
            session_id="session-2",
            faculty_id=10,
        ),
        day=Day.TUESDAY,
    )

    assert not faculty_conflict(first, second)


def test_academic_group_conflict_when_same_group_overlaps():
    first = make_placement(
        session=make_session(session_id="session-1", academic_group_id=30),
    )

    second = make_placement(
        session=make_session(
            session_id="session-2",
            academic_group_id=30,
        ),
        start_period=3,
    )

    assert academic_group_conflict(first, second)


def test_no_academic_group_conflict_when_group_differs():
    first = make_placement(
        session=make_session(session_id="session-1", academic_group_id=30),
    )

    second = make_placement(
        session=make_session(
            session_id="session-2",
            academic_group_id=40,
        ),
        start_period=3,
    )

    assert not academic_group_conflict(first, second)


def test_no_academic_group_conflict_when_times_do_not_overlap():
    first = make_placement(
        session=make_session(session_id="session-1", academic_group_id=30),
    )

    second = make_placement(
        session=make_session(
            session_id="session-2",
            academic_group_id=30,
        ),
        start_period=4,
    )

    assert not academic_group_conflict(first, second)