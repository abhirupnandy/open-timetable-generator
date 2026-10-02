from app.domain.availability import AvailabilityWindow
from app.domain.problem import SchedulingProblem
from app.domain.resource_availability import ResourceAvailability
from app.domain.timetable import (
    Day,
    SchedulingSession,
    TimetableInput,
)
from app.optimisation.solver import solve


def make_problem() -> SchedulingProblem:
    sessions = (
        SchedulingSession(
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
        ),
        SchedulingSession(
            id="assignment:2:session:1",
            teaching_assignment_id=2,
            subject_id=2,
            course_id=1,
            academic_group_id=2,
            faculty_id=2,
            duration_periods=1,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
            session_number=1,
        ),
    )

    return SchedulingProblem(
        timetable_input=TimetableInput(
            days=(Day.MONDAY, Day.TUESDAY),
            periods_per_day=4,
            sessions=sessions,
        ),
    )


def test_solver_places_every_session():
    problem = make_problem()

    result = solve(problem)

    assert len(result.timetable.placements) == 2

    assert {
        placement.session.id
        for placement in result.timetable.placements
    } == {
        "assignment:1:session:1",
        "assignment:2:session:1",
    }


def test_solver_returns_valid_grid_positions():
    problem = make_problem()

    result = solve(problem)

    for placement in result.timetable.placements:
        assert placement.day in (
            Day.MONDAY,
            Day.TUESDAY,
        )
        assert placement.start_period >= 1
        assert placement.end_period <= 4


def test_solver_prevents_faculty_overlap():
    sessions = (
        SchedulingSession(
            id="assignment:1:session:1",
            teaching_assignment_id=1,
            subject_id=1,
            course_id=1,
            academic_group_id=1,
            faculty_id=10,
            duration_periods=2,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
            session_number=1,
        ),
        SchedulingSession(
            id="assignment:2:session:1",
            teaching_assignment_id=2,
            subject_id=2,
            course_id=1,
            academic_group_id=2,
            faculty_id=10,
            duration_periods=2,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
            session_number=1,
        ),
    )

    problem = SchedulingProblem(
        timetable_input=TimetableInput(
            days=(Day.MONDAY,),
            periods_per_day=4,
            sessions=sessions,
        ),
    )

    result = solve(problem)

    first, second = result.timetable.placements

    assert first.day != second.day or (
        first.end_period < second.start_period
        or second.end_period < first.start_period
    )


def test_solver_prevents_academic_group_overlap():
    sessions = (
        SchedulingSession(
            id="assignment:1:session:1",
            teaching_assignment_id=1,
            subject_id=1,
            course_id=1,
            academic_group_id=10,
            faculty_id=1,
            duration_periods=2,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
            session_number=1,
        ),
        SchedulingSession(
            id="assignment:2:session:1",
            teaching_assignment_id=2,
            subject_id=2,
            course_id=1,
            academic_group_id=10,
            faculty_id=2,
            duration_periods=2,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
            session_number=1,
        ),
    )

    problem = SchedulingProblem(
        timetable_input=TimetableInput(
            days=(Day.MONDAY,),
            periods_per_day=4,
            sessions=sessions,
        ),
    )

    result = solve(problem)

    first, second = result.timetable.placements

    assert first.day != second.day or (
        first.end_period < second.start_period
        or second.end_period < first.start_period
    )

def test_solver_assigns_every_session_exactly_once():
    sessions = (
        SchedulingSession(
            id="assignment:1:session:1",
            teaching_assignment_id=1,
            subject_id=1,
            course_id=1,
            academic_group_id=1,
            faculty_id=1,
            duration_periods=1,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
            session_number=1,
        ),
        SchedulingSession(
            id="assignment:1:session:2",
            teaching_assignment_id=1,
            subject_id=1,
            course_id=1,
            academic_group_id=1,
            faculty_id=1,
            duration_periods=1,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
            session_number=2,
        ),
        SchedulingSession(
            id="assignment:2:session:1",
            teaching_assignment_id=2,
            subject_id=2,
            course_id=1,
            academic_group_id=2,
            faculty_id=2,
            duration_periods=1,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
            session_number=1,
        ),
    )

    problem = SchedulingProblem(
        timetable_input=TimetableInput(
            days=(Day.MONDAY,),
            periods_per_day=4,
            sessions=sessions,
        ),
    )

    result = solve(problem)

    placement_ids = [
        placement.session.id
        for placement in result.timetable.placements
    ]

    assert len(placement_ids) == len(sessions)
    assert len(set(placement_ids)) == len(sessions)
    assert set(placement_ids) == {
        "assignment:1:session:1",
        "assignment:1:session:2",
        "assignment:2:session:1",
    }


def test_solver_respects_faculty_availability():
    session = SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=1,
        faculty_id=10,
        duration_periods=2,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )

    problem = SchedulingProblem(
        timetable_input=TimetableInput(
            days=(Day.MONDAY,),
            periods_per_day=4,
            sessions=(session,),
            faculty_availability={
                10: ResourceAvailability(
                    resource_id=10,
                    windows=(
                        AvailabilityWindow(
                            day=Day.MONDAY,
                            start_period=2,
                            end_period=3,
                        ),
                    ),
                ),
            },
        ),
    )

    result = solve(problem)

    assert len(result.timetable.placements) == 1

    placement = result.timetable.placements[0]

    assert placement.session.id == session.id
    assert placement.day == Day.MONDAY
    assert placement.start_period == 2
    assert placement.end_period == 3