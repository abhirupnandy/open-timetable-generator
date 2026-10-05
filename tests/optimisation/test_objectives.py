from ortools.sat.python import cp_model

from app.domain.placement import SessionPlacement
from app.domain.room import RoomType, SchedulingRoom
from app.domain.scheduling_candidate import SchedulingCandidate
from app.domain.timetable import Day, SchedulingSession
from app.optimisation.objectives import build_student_group_gap_objective


def make_candidate(
    session_id: str,
    group_id: int,
    start_period: int,
) -> SchedulingCandidate:
    session = SchedulingSession(
        id=session_id,
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=group_id,
        faculty_id=1,
        duration_periods=1,
        mode="IN_PERSON",
        required_room_type=RoomType.LECTURE_HALL.value,
        session_number=1,
    )

    placement = SessionPlacement(
        session=session,
        day=Day.MONDAY,
        start_period=start_period,
    )

    return SchedulingCandidate(
        placement=placement,
        room=SchedulingRoom(
            id=101,
            room_type=RoomType.LECTURE_HALL,
            capacity=60,
        ),
    )


def solve_gap_objective(
    candidates: tuple[SchedulingCandidate, ...],
) -> int:
    model = cp_model.CpModel()

    candidate_domains = {
        candidate.placement.session.id: (candidate,)
        for candidate in candidates
    }

    candidate_variables = {}

    for session_id in candidate_domains:
        variable = model.new_bool_var(f"{session_id}:candidate")
        model.add(variable == 1)
        candidate_variables[session_id] = [variable]

    objective = build_student_group_gap_objective(
        model,
        candidate_domains,
        candidate_variables,
        days=(Day.MONDAY,),
        periods_per_day=6,
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    )

    return solver.objective_value


def test_group_with_contiguous_sessions_has_no_gaps() -> None:
    candidates = (
        make_candidate("session:1", group_id=1, start_period=1),
        make_candidate("session:2", group_id=1, start_period=2),
        make_candidate("session:3", group_id=1, start_period=3),
    )

    assert solve_gap_objective(candidates) == 0


def test_group_with_internal_free_period_has_gap() -> None:
    candidates = (
        make_candidate("session:1", group_id=1, start_period=1),
        make_candidate("session:2", group_id=1, start_period=3),
    )

    assert solve_gap_objective(candidates) == 1


def test_free_periods_before_and_after_sessions_are_not_gaps() -> None:
    candidates = (
        make_candidate("session:1", group_id=1, start_period=2),
        make_candidate("session:2", group_id=1, start_period=3),
    )

    assert solve_gap_objective(candidates) == 0
