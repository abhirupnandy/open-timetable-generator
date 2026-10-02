from app.domain.hard_constraints import HardConflictReason
from app.domain.placement import SessionPlacement
from app.domain.schedule import Timetable
from app.domain.timetable import Day, SchedulingSession
from app.domain.validator import validate_timetable


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


def test_empty_timetable_is_valid():
    result = validate_timetable(Timetable.empty())

    assert result.is_valid
    assert result.conflicts == ()


def test_non_conflicting_timetable_is_valid():
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

    timetable = Timetable(
        placements=(first, second),
    )

    result = validate_timetable(timetable)

    assert result.is_valid
    assert result.conflicts == ()


def test_validator_detects_faculty_conflict():
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

    timetable = Timetable(
        placements=(first, second),
    )

    result = validate_timetable(timetable)

    assert not result.is_valid

    conflict = result.conflicts[0]

    assert conflict.first_session_id == "session-1"
    assert conflict.second_session_id == "session-2"
    assert conflict.reasons == (HardConflictReason.FACULTY,)


def test_validator_detects_academic_group_conflict():
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

    timetable = Timetable(
        placements=(first, second),
    )

    result = validate_timetable(timetable)

    assert not result.is_valid
    assert len(result.conflicts) == 1

    conflict = result.conflicts[0]

    assert conflict.first_session_id == "session-1"
    assert conflict.second_session_id == "session-2"
    assert conflict.reasons == (HardConflictReason.ACADEMIC_GROUP,)


def test_validator_reports_multiple_conflicts():
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

    third = make_placement(
        make_session(
            session_id="session-3",
            faculty_id=30,
            academic_group_id=20,
        ),
        start_period=3,
    )

    timetable = Timetable(
        placements=(first, second, third),
    )

    result = validate_timetable(timetable)

    assert not result.is_valid
    assert len(result.conflicts) == 2