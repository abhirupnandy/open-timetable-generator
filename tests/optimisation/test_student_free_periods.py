from __future__ import annotations

from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.schedule import Timetable
from app.domain.timetable import SchedulingSession
from app.optimisation.student_free_periods import (
    calculate_student_free_period_penalty,
)


def make_placement(
    *,
    session_id: str,
    group_id: int,
    start_period: int,
    duration_periods: int = 1,
    day: Day = Day.MONDAY,
) -> SessionPlacement:
    session = SchedulingSession(
        id=session_id,
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=group_id,
        faculty_id=1,
        duration_periods=duration_periods,
        mode="ONLINE",
        required_room_type=None,
        session_number=1,
    )

    return SessionPlacement(
        session=session,
        day=day,
        start_period=start_period,
    )


def test_two_free_periods_have_no_penalty() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                start_period=2,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                start_period=3,
            ),
            make_placement(
                session_id="s4",
                group_id=1,
                start_period=4,
            ),
            make_placement(
                session_id="s5",
                group_id=1,
                start_period=5,
            ),
            make_placement(
                session_id="s6",
                group_id=1,
                start_period=6,
            ),
        )
    )

    assert calculate_student_free_period_penalty(
        timetable,
        periods_per_day=8,
    ) == 0


def test_three_free_periods_have_no_penalty() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                start_period=2,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                start_period=3,
            ),
            make_placement(
                session_id="s4",
                group_id=1,
                start_period=4,
            ),
            make_placement(
                session_id="s5",
                group_id=1,
                start_period=5,
            ),
        )
    )

    assert calculate_student_free_period_penalty(
        timetable,
        periods_per_day=8,
    ) == 0


def test_one_free_period_has_penalty_one() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                start_period=2,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                start_period=3,
            ),
            make_placement(
                session_id="s4",
                group_id=1,
                start_period=4,
            ),
            make_placement(
                session_id="s5",
                group_id=1,
                start_period=5,
            ),
            make_placement(
                session_id="s6",
                group_id=1,
                start_period=6,
            ),
            make_placement(
                session_id="s7",
                group_id=1,
                start_period=7,
            ),
        )
    )

    assert calculate_student_free_period_penalty(
        timetable,
        periods_per_day=8,
    ) == 1


def test_zero_free_periods_have_penalty_two() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                start_period=2,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                start_period=3,
            ),
            make_placement(
                session_id="s4",
                group_id=1,
                start_period=4,
            ),
            make_placement(
                session_id="s5",
                group_id=1,
                start_period=5,
            ),
            make_placement(
                session_id="s6",
                group_id=1,
                start_period=6,
            ),
            make_placement(
                session_id="s7",
                group_id=1,
                start_period=7,
            ),
            make_placement(
                session_id="s8",
                group_id=1,
                start_period=8,
            ),
        )
    )

    assert calculate_student_free_period_penalty(
        timetable,
        periods_per_day=8,
    ) == 2


def test_free_periods_do_not_need_to_be_consecutive() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                start_period=3,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                start_period=4,
            ),
            make_placement(
                session_id="s4",
                group_id=1,
                start_period=6,
            ),
            make_placement(
                session_id="s5",
                group_id=1,
                start_period=7,
            ),
            make_placement(
                session_id="s6",
                group_id=1,
                start_period=8,
            ),
        )
    )

    assert calculate_student_free_period_penalty(
        timetable,
        periods_per_day=8,
    ) == 0


def test_free_periods_are_calculated_independently_per_group() -> None:
    timetable = Timetable(
        placements=(
            # Group 1: 2 free periods -> penalty 0
            make_placement(
                session_id="g1s1",
                group_id=1,
                start_period=1,
            ),
            make_placement(
                session_id="g1s2",
                group_id=1,
                start_period=2,
            ),
            make_placement(
                session_id="g1s3",
                group_id=1,
                start_period=3,
            ),
            make_placement(
                session_id="g1s4",
                group_id=1,
                start_period=4,
            ),
            make_placement(
                session_id="g1s5",
                group_id=1,
                start_period=5,
            ),
            make_placement(
                session_id="g1s6",
                group_id=1,
                start_period=6,
            ),
            # Group 2: 0 free periods -> penalty 2
            make_placement(
                session_id="g2s1",
                group_id=2,
                start_period=1,
            ),
            make_placement(
                session_id="g2s2",
                group_id=2,
                start_period=2,
            ),
            make_placement(
                session_id="g2s3",
                group_id=2,
                start_period=3,
            ),
            make_placement(
                session_id="g2s4",
                group_id=2,
                start_period=4,
            ),
            make_placement(
                session_id="g2s5",
                group_id=2,
                start_period=5,
            ),
            make_placement(
                session_id="g2s6",
                group_id=2,
                start_period=6,
            ),
            make_placement(
                session_id="g2s7",
                group_id=2,
                start_period=7,
            ),
            make_placement(
                session_id="g2s8",
                group_id=2,
                start_period=8,
            ),
        )
    )

    assert calculate_student_free_period_penalty(
        timetable,
        periods_per_day=8,
    ) == 2


def test_free_periods_are_calculated_independently_per_day() -> None:
    timetable = Timetable(
        placements=(
            # Monday: 2 free periods -> penalty 0
            make_placement(
                session_id="mon1",
                group_id=1,
                start_period=1,
                day=Day.MONDAY,
            ),
            make_placement(
                session_id="mon2",
                group_id=1,
                start_period=2,
                day=Day.MONDAY,
            ),
            make_placement(
                session_id="mon3",
                group_id=1,
                start_period=3,
                day=Day.MONDAY,
            ),
            make_placement(
                session_id="mon4",
                group_id=1,
                start_period=4,
                day=Day.MONDAY,
            ),
            make_placement(
                session_id="mon5",
                group_id=1,
                start_period=5,
                day=Day.MONDAY,
            ),
            make_placement(
                session_id="mon6",
                group_id=1,
                start_period=6,
                day=Day.MONDAY,
            ),
            # Tuesday: 0 free periods -> penalty 2
            make_placement(
                session_id="tue1",
                group_id=1,
                start_period=1,
                day=Day.TUESDAY,
            ),
            make_placement(
                session_id="tue2",
                group_id=1,
                start_period=2,
                day=Day.TUESDAY,
            ),
            make_placement(
                session_id="tue3",
                group_id=1,
                start_period=3,
                day=Day.TUESDAY,
            ),
            make_placement(
                session_id="tue4",
                group_id=1,
                start_period=4,
                day=Day.TUESDAY,
            ),
            make_placement(
                session_id="tue5",
                group_id=1,
                start_period=5,
                day=Day.TUESDAY,
            ),
            make_placement(
                session_id="tue6",
                group_id=1,
                start_period=6,
                day=Day.TUESDAY,
            ),
            make_placement(
                session_id="tue7",
                group_id=1,
                start_period=7,
                day=Day.TUESDAY,
            ),
            make_placement(
                session_id="tue8",
                group_id=1,
                start_period=8,
                day=Day.TUESDAY,
            ),
        )
    )

    assert calculate_student_free_period_penalty(
        timetable,
        periods_per_day=8,
    ) == 2


def test_multi_period_session_occupies_each_period() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="lab1",
                group_id=1,
                start_period=1,
                duration_periods=2,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                start_period=3,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                start_period=4,
            ),
            make_placement(
                session_id="s4",
                group_id=1,
                start_period=5,
            ),
            make_placement(
                session_id="s5",
                group_id=1,
                start_period=6,
            ),
            make_placement(
                session_id="s6",
                group_id=1,
                start_period=7,
            ),
        )
    )

    # P8 is the only free period.
    assert calculate_student_free_period_penalty(
        timetable,
        periods_per_day=8,
    ) == 1


def test_lunch_is_not_counted_as_a_free_period() -> None:
    """
    Lunch is outside the timetable period model.

    The timetable has eight academic periods; lunch does not
    create an additional period and therefore must not contribute
    to the two-period free-time requirement.
    """

    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                start_period=2,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                start_period=3,
            ),
            make_placement(
                session_id="s4",
                group_id=1,
                start_period=4,
            ),
            make_placement(
                session_id="s5",
                group_id=1,
                start_period=5,
            ),
            make_placement(
                session_id="s6",
                group_id=1,
                start_period=6,
            ),
            make_placement(
                session_id="s7",
                group_id=1,
                start_period=7,
            ),
        )
    )

    # Only P8 is free. Lunch is not represented as a period.
    assert calculate_student_free_period_penalty(
        timetable,
        periods_per_day=8,
    ) == 1


def test_invalid_period_count_is_rejected() -> None:
    timetable = Timetable(placements=())

    try:
        calculate_student_free_period_penalty(
            timetable,
            periods_per_day=0,
        )
    except ValueError:
        return

    raise AssertionError("Expected ValueError for non-positive periods_per_day")