from app.domain.problem import SchedulingProblem, SchedulingSolution
from app.domain.schedule import Timetable
from app.domain.timetable import (
    Day,
    SchedulingSession,
    TimetableInput,
)


def make_input() -> TimetableInput:
    session = SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=1,
        faculty_id=1,
        duration_periods=2,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )

    return TimetableInput(
        days=(Day.MONDAY, Day.TUESDAY),
        periods_per_day=8,
        sessions=(session,),
    )


def test_scheduling_problem_exposes_sessions():
    timetable_input = make_input()

    problem = SchedulingProblem(
        timetable_input=timetable_input,
    )

    assert problem.timetable_input == timetable_input
    assert problem.sessions == timetable_input.sessions


def test_scheduling_solution_contains_timetable():
    timetable = Timetable.empty()

    solution = SchedulingSolution(
        timetable=timetable,
    )

    assert solution.timetable is timetable