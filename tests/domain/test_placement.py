from app.domain.placement import SessionPlacement, is_valid_placement, placements_overlap
from app.domain.timetable import Day, SchedulingSession


def make_session(
    *,
    duration_periods: int = 2,
) -> SchedulingSession:
    return SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=10,
        course_id=20,
        academic_group_id=30,
        faculty_id=40,
        duration_periods=duration_periods,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )


def test_session_placement_calculates_end_period():
    placement = SessionPlacement(
        session=make_session(duration_periods=2),
        day=Day.WEDNESDAY,
        start_period=3,
    )

    assert placement.day == Day.WEDNESDAY
    assert placement.start_period == 3
    assert placement.end_period == 4


def test_session_placement_returns_occupied_periods():
    placement = SessionPlacement(
        session=make_session(duration_periods=3),
        day=Day.FRIDAY,
        start_period=4,
    )

    assert placement.occupied_periods == (4, 5, 6)


def test_single_period_session():
    placement = SessionPlacement(
        session=make_session(duration_periods=1),
        day=Day.MONDAY,
        start_period=8,
    )

    assert placement.end_period == 8
    assert placement.occupied_periods == (8,)

def test_valid_placement():
    placement = SessionPlacement(
        session=make_session(duration_periods=2),
        day=Day.WEDNESDAY,
        start_period=7,
    )

    assert is_valid_placement(
        placement,
        days=(
            Day.MONDAY,
            Day.TUESDAY,
            Day.WEDNESDAY,
            Day.THURSDAY,
            Day.FRIDAY,
        ),
        periods_per_day=8,
    )


def test_placement_cannot_extend_beyond_day():
    placement = SessionPlacement(
        session=make_session(duration_periods=2),
        day=Day.WEDNESDAY,
        start_period=8,
    )

    assert not is_valid_placement(
        placement,
        days=(
            Day.MONDAY,
            Day.TUESDAY,
            Day.WEDNESDAY,
            Day.THURSDAY,
            Day.FRIDAY,
        ),
        periods_per_day=8,
    )


def test_placement_cannot_use_unconfigured_day():
    placement = SessionPlacement(
        session=make_session(duration_periods=1),
        day=Day.SATURDAY,
        start_period=1,
    )

    assert not is_valid_placement(
        placement,
        days=(
            Day.MONDAY,
            Day.TUESDAY,
            Day.WEDNESDAY,
            Day.THURSDAY,
            Day.FRIDAY,
        ),
        periods_per_day=8,
    )


def test_placement_cannot_start_before_period_one():
    placement = SessionPlacement(
        session=make_session(duration_periods=1),
        day=Day.MONDAY,
        start_period=0,
    )

    assert not is_valid_placement(
        placement,
        days=(
            Day.MONDAY,
            Day.TUESDAY,
            Day.WEDNESDAY,
            Day.THURSDAY,
            Day.FRIDAY,
        ),
        periods_per_day=8,
    )

def test_placements_overlap_on_same_day():
    first = SessionPlacement(
        session=make_session(duration_periods=2),
        day=Day.MONDAY,
        start_period=2,
    )

    second = SessionPlacement(
        session=make_session(duration_periods=2),
        day=Day.MONDAY,
        start_period=3,
    )

    assert placements_overlap(first, second)


def test_placements_do_not_overlap_when_adjacent():
    first = SessionPlacement(
        session=make_session(duration_periods=2),
        day=Day.MONDAY,
        start_period=2,
    )

    second = SessionPlacement(
        session=make_session(duration_periods=2),
        day=Day.MONDAY,
        start_period=4,
    )

    assert not placements_overlap(first, second)


def test_placements_on_different_days_do_not_overlap():
    first = SessionPlacement(
        session=make_session(duration_periods=2),
        day=Day.MONDAY,
        start_period=2,
    )

    second = SessionPlacement(
        session=make_session(duration_periods=2),
        day=Day.TUESDAY,
        start_period=2,
    )

    assert not placements_overlap(first, second)


def test_identical_placements_overlap():
    first = SessionPlacement(
        session=make_session(duration_periods=1),
        day=Day.WEDNESDAY,
        start_period=5,
    )

    second = SessionPlacement(
        session=make_session(duration_periods=1),
        day=Day.WEDNESDAY,
        start_period=5,
    )

    assert placements_overlap(first, second)