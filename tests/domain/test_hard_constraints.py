from app.domain.hard_constraints import (
    HardConflictReason,
    hard_conflict_reasons,
    has_hard_conflict,
)
from app.domain.placement import SessionPlacement
from app.domain.timetable import Day, SchedulingSession


def make_session(
    *,
    session_id: str,
    faculty_id: int = 10,
    academic_group_id: int = 20,
) -> SchedulingSession:
    return SchedulingSession(
        id=session_id,
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=academic_group_id,
        faculty_id=faculty_id,
        duration_periods=2,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )


def make_placement(
    session: SchedulingSession,
    *,
    day: Day = Day.MONDAY,
    start_period: int = 2,
) -> SessionPlacement:
    return SessionPlacement(
        session=session,
        day=day,
        start_period=start_period,
    )


def test_detects_faculty_hard_conflict():
    first = make_placement(
        make_session(
            session_id="session-1",
            faculty_id=10,
            academic_group_id=20,
        ),
    )

    second = make_placement(
        make_session(
            session_id="session-2",
            faculty_id=10,
            academic_group_id=30,
        ),
        start_period=3,
    )

    assert has_hard_conflict(first, second)


def test_detects_academic_group_hard_conflict():
    first = make_placement(
        make_session(
            session_id="session-1",
            faculty_id=10,
            academic_group_id=20,
        ),
    )

    second = make_placement(
        make_session(
            session_id="session-2",
            faculty_id=30,
            academic_group_id=20,
        ),
        start_period=3,
    )

    assert has_hard_conflict(first, second)


def test_no_hard_conflict_for_independent_overlapping_sessions():
    first = make_placement(
        make_session(
            session_id="session-1",
            faculty_id=10,
            academic_group_id=20,
        ),
    )

    second = make_placement(
        make_session(
            session_id="session-2",
            faculty_id=30,
            academic_group_id=40,
        ),
        start_period=3,
    )

    assert not has_hard_conflict(first, second)


def test_no_hard_conflict_when_sessions_do_not_overlap():
    first = make_placement(
        make_session(
            session_id="session-1",
            faculty_id=10,
            academic_group_id=20,
        ),
    )

    second = make_placement(
        make_session(
            session_id="session-2",
            faculty_id=10,
            academic_group_id=20,
        ),
        start_period=4,
    )

    assert not has_hard_conflict(first, second)

def test_hard_conflict_reasons_identify_faculty_conflict():
    first = make_placement(
        make_session(
            session_id="session-1",
            faculty_id=10,
            academic_group_id=20,
        ),
    )

    second = make_placement(
        make_session(
            session_id="session-2",
            faculty_id=10,
            academic_group_id=30,
        ),
        start_period=3,
    )

    assert hard_conflict_reasons(first, second) == (
        HardConflictReason.FACULTY,
    )


def test_hard_conflict_reasons_identify_academic_group_conflict():
    first = make_placement(
        make_session(
            session_id="session-1",
            faculty_id=10,
            academic_group_id=20,
        ),
    )

    second = make_placement(
        make_session(
            session_id="session-2",
            faculty_id=30,
            academic_group_id=20,
        ),
        start_period=3,
    )

    assert hard_conflict_reasons(first, second) == (
        HardConflictReason.ACADEMIC_GROUP,
    )


def test_hard_conflict_reasons_can_contain_multiple_reasons():
    first = make_placement(
        make_session(
            session_id="session-1",
            faculty_id=10,
            academic_group_id=20,
        ),
    )

    second = make_placement(
        make_session(
            session_id="session-2",
            faculty_id=10,
            academic_group_id=20,
        ),
        start_period=3,
    )

    assert hard_conflict_reasons(first, second) == (
        HardConflictReason.FACULTY,
        HardConflictReason.ACADEMIC_GROUP,
    )


def test_hard_conflict_reasons_empty_for_valid_pair():
    first = make_placement(
        make_session(
            session_id="session-1",
            faculty_id=10,
            academic_group_id=20,
        ),
    )

    second = make_placement(
        make_session(
            session_id="session-2",
            faculty_id=30,
            academic_group_id=40,
        ),
        start_period=3,
    )

    assert hard_conflict_reasons(first, second) == ()