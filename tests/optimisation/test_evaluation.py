from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.schedule import Timetable
from app.domain.timetable import SchedulingSession
from app.optimisation.evaluation import calculate_student_group_gaps


def make_placement(*, session_id: str, group_id: int, start_period: int) -> SessionPlacement:
    session = SchedulingSession(
        id=session_id,
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=group_id,
        faculty_id=1,
        duration_periods=1,
        mode="ONLINE",
        required_room_type=None,
        session_number=1,
    )

    return SessionPlacement(
        session=session,
        day=Day.MONDAY,
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