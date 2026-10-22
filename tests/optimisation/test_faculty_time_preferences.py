from app.db.models.faculty import FacultyTimePreference
from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.schedule import Timetable
from app.domain.timetable import SchedulingSession
from app.optimisation.faculty_time_preferences import (
    calculate_s3_penalty,
)


def _session(
    *,
    faculty_id: int = 1,
    duration_periods: int = 1,
) -> SchedulingSession:
    return SchedulingSession(
        id="session-1",
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=1,
        faculty_id=faculty_id,
        duration_periods=duration_periods,
        mode="IN_PERSON",
        required_room_type=None,
        session_number=1,
    )


def _placement(
    *,
    period: int,
    duration_periods: int = 1,
    faculty_id: int = 1,
) -> SessionPlacement:
    return SessionPlacement(
        session=_session(
            faculty_id=faculty_id,
            duration_periods=duration_periods,
        ),
        day=Day.MONDAY,
        start_period=period,
    )


def test_any_preference_has_no_penalty() -> None:
    timetable = Timetable(
        placements=(
            _placement(period=1),
            _placement(period=8),
        )
    )

    penalty = calculate_s3_penalty(
        timetable,
        faculty_time_preferences={
            1: FacultyTimePreference.ANY.value,
        },
    )

    assert penalty == 0


def test_morning_preference_penalises_afternoon_period() -> None:
    timetable = Timetable(
        placements=(
            _placement(period=5),
        )
    )

    penalty = calculate_s3_penalty(
        timetable,
        faculty_time_preferences={
            1: FacultyTimePreference.MORNING.value,
        },
    )

    assert penalty == 1


def test_morning_preference_accepts_morning_period() -> None:
    timetable = Timetable(
        placements=(
            _placement(period=4),
        )
    )

    penalty = calculate_s3_penalty(
        timetable,
        faculty_time_preferences={
            1: FacultyTimePreference.MORNING.value,
        },
    )

    assert penalty == 0


def test_afternoon_preference_penalises_morning_period() -> None:
    timetable = Timetable(
        placements=(
            _placement(period=3),
        )
    )

    penalty = calculate_s3_penalty(
        timetable,
        faculty_time_preferences={
            1: FacultyTimePreference.AFTERNOON.value,
        },
    )

    assert penalty == 1


def test_afternoon_preference_accepts_afternoon_period() -> None:
    timetable = Timetable(
        placements=(
            _placement(period=6),
        )
    )

    penalty = calculate_s3_penalty(
        timetable,
        faculty_time_preferences={
            1: FacultyTimePreference.AFTERNOON.value,
        },
    )

    assert penalty == 0


def test_evening_preference_penalises_period_before_evening() -> None:
    timetable = Timetable(
        placements=(
            _placement(period=6),
        )
    )

    penalty = calculate_s3_penalty(
        timetable,
        faculty_time_preferences={
            1: FacultyTimePreference.EVENING.value,
        },
    )

    assert penalty == 1


def test_evening_preference_accepts_evening_period() -> None:
    timetable = Timetable(
        placements=(
            _placement(period=7),
            _placement(period=8),
        )
    )

    penalty = calculate_s3_penalty(
        timetable,
        faculty_time_preferences={
            1: FacultyTimePreference.EVENING.value,
        },
    )

    assert penalty == 0


def test_multi_period_session_counts_each_unpreferred_period() -> None:
    timetable = Timetable(
        placements=(
            _placement(
                period=4,
                duration_periods=2,
            ),
        )
    )

    penalty = calculate_s3_penalty(
        timetable,
        faculty_time_preferences={
            1: FacultyTimePreference.MORNING.value,
        },
    )

    assert penalty == 1


def test_missing_faculty_preference_means_no_penalty() -> None:
    timetable = Timetable(
        placements=(
            _placement(period=8),
        )
    )

    penalty = calculate_s3_penalty(
        timetable,
        faculty_time_preferences={},
    )

    assert penalty == 0


def test_unknown_preference_raises_value_error() -> None:
    timetable = Timetable(
        placements=(
            _placement(period=1),
        )
    )

    try:
        calculate_s3_penalty(
            timetable,
            faculty_time_preferences={
                1: "INVALID",
            },
        )
    except ValueError as exc:
        assert "Unknown faculty time preference" in str(exc)
    else:
        raise AssertionError("Expected ValueError")