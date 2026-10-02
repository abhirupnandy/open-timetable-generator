from app.db.models import AssignmentMode, TeachingAssignment
from app.domain.availability import AvailabilityWindow
from app.domain.input_builder import build_timetable_input
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import RoomType, SchedulingRoom
from app.domain.timetable import Day


def make_assignment(
    *,
    assignment_id: int = 1,
    sessions_per_week: int = 2,
    duration_periods: int = 1,
    is_active: bool = True,
) -> TeachingAssignment:
    return TeachingAssignment(
        id=assignment_id,
        subject_id=10,
        course_id=20,
        academic_group_id=30,
        faculty_id=40,
        sessions_per_week=sessions_per_week,
        duration_periods=duration_periods,
        mode=AssignmentMode.IN_PERSON,
        required_room_type="LECTURE_HALL",
        is_active=is_active,
    )


def test_build_timetable_input_expands_active_assignments():
    assignment = make_assignment(
        assignment_id=7,
        sessions_per_week=3,
        duration_periods=2,
    )

    timetable_input = build_timetable_input([assignment])

    assert timetable_input.days == (
        Day.MONDAY,
        Day.TUESDAY,
        Day.WEDNESDAY,
        Day.THURSDAY,
        Day.FRIDAY,
    )

    assert timetable_input.periods_per_day == 8

    assert len(timetable_input.sessions) == 3

    assert [session.id for session in timetable_input.sessions] == [
        "assignment:7:session:1",
        "assignment:7:session:2",
        "assignment:7:session:3",
    ]

    assert all(session.duration_periods == 2 for session in timetable_input.sessions)


def test_build_timetable_input_ignores_inactive_assignments():
    active = make_assignment(
        assignment_id=1,
        sessions_per_week=2,
    )

    inactive = make_assignment(
        assignment_id=2,
        sessions_per_week=3,
        is_active=False,
    )

    timetable_input = build_timetable_input([active, inactive])

    assert len(timetable_input.sessions) == 2

    assert all(
        session.teaching_assignment_id == 1
        for session in timetable_input.sessions
    )


def test_build_timetable_input_accepts_custom_grid():
    assignment = make_assignment()

    timetable_input = build_timetable_input(
        [assignment],
        days=(Day.MONDAY, Day.WEDNESDAY),
        periods_per_day=6,
    )

    assert timetable_input.days == (
        Day.MONDAY,
        Day.WEDNESDAY,
    )

    assert timetable_input.periods_per_day == 6


def test_build_timetable_input_rejects_invalid_grid():
    assignment = make_assignment()

    try:
        build_timetable_input(
            [assignment],
            periods_per_day=0,
        )
    except ValueError as exc:
        assert str(exc) == "periods_per_day must be greater than 0"
    else:
        raise AssertionError("Expected ValueError")


def test_build_timetable_input_rejects_empty_days():
    assignment = make_assignment()

    try:
        build_timetable_input(
            [assignment],
            days=(),
        )
    except ValueError as exc:
        assert str(exc) == "At least one timetable day is required"
    else:
        raise AssertionError("Expected ValueError")


def test_build_timetable_input_includes_academic_group_capacities():
    assignment = TeachingAssignment(
        id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=10,
        faculty_id=20,
        sessions_per_week=2,
        duration_periods=1,
        mode=AssignmentMode.IN_PERSON,
        required_room_type="LECTURE_HALL",
        is_active=True,
    )

    availability = {
        10: ResourceAvailability(
            resource_id=10,
            windows=(
                AvailabilityWindow(
                    day=Day.MONDAY,
                    start_period=1,
                    end_period=4,
                ),
            ),
        ),
    }

    result = build_timetable_input(
        [assignment],
        room_availability=availability,
    )

    assert result.room_availability == availability

def test_build_timetable_input_includes_rooms():
    assignment = make_assignment()

    rooms = (
        SchedulingRoom(
            id=101,
            room_type=RoomType.LECTURE_HALL,
            capacity=60,
        ),
        SchedulingRoom(
            id=102,
            room_type=RoomType.CLASSROOM,
            capacity=40,
        ),
    )

    result = build_timetable_input(
        [assignment],
        rooms=rooms,
    )

    assert result.rooms == rooms