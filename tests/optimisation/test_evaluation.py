from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.schedule import Timetable
from app.domain.timetable import SchedulingSession
from app.optimisation.evaluation import (
    calculate_student_group_gaps,
    calculate_subject_spreading_penalty,
)


def make_placement(
    *,
    session_id: str,
    group_id: int,
    start_period: int,
    subject_id: int = 1,
    day: Day = Day.MONDAY,
    duration_periods: int = 1,
) -> SessionPlacement:
    session = SchedulingSession(
        id=session_id,
        teaching_assignment_id=1,
        subject_id=subject_id,
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


def test_contiguous_sessions_have_no_gaps() -> None:
    timetable = Timetable(
        placements=(
            make_placement(session_id="s1", group_id=1, start_period=1),
            make_placement(session_id="s2", group_id=1, start_period=2),
            make_placement(session_id="s3", group_id=1, start_period=3),
        )
    )

    assert calculate_student_group_gaps(
        timetable,
        periods_per_day=8,
    ) == 0


def test_sessions_with_internal_gap_count_one_gap() -> None:
    timetable = Timetable(
        placements=(
            make_placement(session_id="s1", group_id=1, start_period=1),
            make_placement(session_id="s2", group_id=1, start_period=3),
        )
    )

    assert calculate_student_group_gaps(
        timetable,
        periods_per_day=8,
    ) == 1


def test_gaps_are_calculated_per_group_and_day() -> None:
    timetable = Timetable(
        placements=(
            make_placement(session_id="s1", group_id=1, start_period=1),
            make_placement(session_id="s2", group_id=1, start_period=3),
            make_placement(session_id="s3", group_id=2, start_period=2),
            make_placement(session_id="s4", group_id=2, start_period=4),
        )
    )

    assert calculate_student_group_gaps(
        timetable,
        periods_per_day=8,
    ) == 2


def test_subject_spreading_has_no_penalty_when_sessions_are_on_different_days() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                subject_id=101,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                subject_id=101,
                day=Day.WEDNESDAY,
                start_period=1,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                subject_id=101,
                day=Day.FRIDAY,
                start_period=1,
            ),
        )
    )

    assert calculate_subject_spreading_penalty(timetable) == 0


def test_subject_spreading_penalises_two_sessions_on_same_day() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                subject_id=101,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                subject_id=101,
                day=Day.MONDAY,
                start_period=3,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                subject_id=101,
                day=Day.WEDNESDAY,
                start_period=1,
            ),
        )
    )

    assert calculate_subject_spreading_penalty(timetable) == 1


def test_subject_spreading_penalises_three_sessions_on_same_day_by_two() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                subject_id=101,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                subject_id=101,
                day=Day.MONDAY,
                start_period=2,
            ),
            make_placement(
                session_id="s3",
                group_id=1,
                subject_id=101,
                day=Day.MONDAY,
                start_period=3,
            ),
        )
    )

    assert calculate_subject_spreading_penalty(timetable) == 2


def test_subject_spreading_does_not_mix_different_subjects() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                subject_id=101,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                subject_id=102,
                day=Day.MONDAY,
                start_period=2,
            ),
        )
    )

    assert calculate_subject_spreading_penalty(timetable) == 0


def test_subject_spreading_does_not_mix_different_groups() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                subject_id=101,
                day=Day.MONDAY,
                start_period=1,
            ),
            make_placement(
                session_id="s2",
                group_id=2,
                subject_id=101,
                day=Day.MONDAY,
                start_period=2,
            ),
        )
    )

    assert calculate_subject_spreading_penalty(timetable) == 0


def test_subject_spreading_counts_multi_period_session_once() -> None:
    timetable = Timetable(
        placements=(
            make_placement(
                session_id="s1",
                group_id=1,
                subject_id=101,
                day=Day.MONDAY,
                start_period=1,
                duration_periods=2,
            ),
            make_placement(
                session_id="s2",
                group_id=1,
                subject_id=101,
                day=Day.WEDNESDAY,
                start_period=3,
                duration_periods=2,
            ),
        )
    )

    assert calculate_subject_spreading_penalty(timetable) == 0