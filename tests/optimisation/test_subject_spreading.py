from __future__ import annotations

from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.schedule import Timetable
from app.domain.timetable import SchedulingSession
from app.optimisation.subject_spreading import calculate_s4_penalty


def _session(
    session_id: str,
    *,
    subject_id: int,
    academic_group_id: int,
    duration_periods: int = 1,
) -> SchedulingSession:
    return SchedulingSession(
        id=session_id,
        teaching_assignment_id=1,
        subject_id=subject_id,
        course_id=1,
        academic_group_id=academic_group_id,
        faculty_id=1,
        duration_periods=duration_periods,
        mode="IN_PERSON",
        required_room_type=None,
        session_number=1,
    )


def _placement(
    session_id: str,
    *,
    subject_id: int,
    academic_group_id: int,
    day: Day,
    start_period: int,
    duration_periods: int = 1,
) -> SessionPlacement:
    return SessionPlacement(
        session=_session(
            session_id,
            subject_id=subject_id,
            academic_group_id=academic_group_id,
            duration_periods=duration_periods,
        ),
        day=day,
        start_period=start_period,
    )


def test_s4_no_penalty_when_subject_is_spread_across_days() -> None:
    timetable = Timetable(
        placements=(
            _placement(
                "session-1",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=1,
            ),
            _placement(
                "session-2",
                subject_id=101,
                academic_group_id=1,
                day=Day.WEDNESDAY,
                start_period=2,
            ),
            _placement(
                "session-3",
                subject_id=101,
                academic_group_id=1,
                day=Day.FRIDAY,
                start_period=3,
            ),
        ),
    )

    assert calculate_s4_penalty(timetable) == 0


def test_s4_penalises_multiple_occurrences_of_same_subject_on_one_day() -> None:
    timetable = Timetable(
        placements=(
            _placement(
                "session-1",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=1,
            ),
            _placement(
                "session-2",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=3,
            ),
            _placement(
                "session-3",
                subject_id=101,
                academic_group_id=1,
                day=Day.THURSDAY,
                start_period=2,
            ),
        ),
    )

    assert calculate_s4_penalty(timetable) == 1


def test_s4_three_occurrences_on_one_day_have_penalty_two() -> None:
    timetable = Timetable(
        placements=(
            _placement(
                "session-1",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=1,
            ),
            _placement(
                "session-2",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=2,
            ),
            _placement(
                "session-3",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=3,
            ),
        ),
    )

    assert calculate_s4_penalty(timetable) == 2


def test_s4_does_not_mix_different_subjects() -> None:
    timetable = Timetable(
        placements=(
            _placement(
                "session-1",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=1,
            ),
            _placement(
                "session-2",
                subject_id=102,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=2,
            ),
        ),
    )

    assert calculate_s4_penalty(timetable) == 0


def test_s4_does_not_mix_different_academic_groups() -> None:
    timetable = Timetable(
        placements=(
            _placement(
                "session-1",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=1,
            ),
            _placement(
                "session-2",
                subject_id=101,
                academic_group_id=2,
                day=Day.MONDAY,
                start_period=2,
            ),
        ),
    )

    assert calculate_s4_penalty(timetable) == 0


def test_s4_counts_penalties_independently_per_subject_group_and_day() -> None:
    timetable = Timetable(
        placements=(
            # Subject 101 / Group 1 / Monday -> penalty 1
            _placement(
                "session-1",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=1,
            ),
            _placement(
                "session-2",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=3,
            ),
            # Subject 101 / Group 1 / Wednesday -> penalty 0
            _placement(
                "session-3",
                subject_id=101,
                academic_group_id=1,
                day=Day.WEDNESDAY,
                start_period=2,
            ),
            # Subject 102 / Group 1 / Monday -> penalty 2
            _placement(
                "session-4",
                subject_id=102,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=4,
            ),
            _placement(
                "session-5",
                subject_id=102,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=5,
            ),
            _placement(
                "session-6",
                subject_id=102,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=7,
            ),
        ),
    )

    assert calculate_s4_penalty(timetable) == 3


def test_s4_multi_period_session_counts_as_one_occurrence() -> None:
    timetable = Timetable(
        placements=(
            _placement(
                "session-1",
                subject_id=101,
                academic_group_id=1,
                day=Day.MONDAY,
                start_period=1,
                duration_periods=2,
            ),
            _placement(
                "session-2",
                subject_id=101,
                academic_group_id=1,
                day=Day.WEDNESDAY,
                start_period=3,
                duration_periods=2,
            ),
        ),
    )

    assert calculate_s4_penalty(timetable) == 0