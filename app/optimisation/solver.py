from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.domain.conflicts import academic_group_conflict
from app.domain.placement import SessionPlacement
from app.domain.problem import SchedulingProblem
from app.domain.room_assignment import RoomAssignment
from app.domain.schedule import Timetable
from app.domain.scheduling_candidate import SchedulingCandidate
from app.domain.scheduling_candidate_domains import (
    build_scheduling_candidate_domains,
)
from app.optimisation.objectives import build_student_group_gap_objective


@dataclass(frozen=True)
class SolverResult:
    """Result returned by the CP-SAT solver."""

    timetable: Timetable


def _placements_overlap(
    first: SessionPlacement,
    second: SessionPlacement,
) -> bool:
    """Return whether two candidate placements occupy overlapping periods."""

    if first.day != second.day:
        return False

    return (
        first.start_period <= second.end_period
        and second.start_period <= first.end_period
    )


def _add_pairwise_candidate_conflict_constraints(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    conflicts,
) -> None:
    """Prevent incompatible scheduling candidates from being selected together."""

    session_items = list(candidate_domains.items())

    for first_index, (first_session_id, first_candidates) in enumerate(
        session_items
    ):
        for second_session_id, second_candidates in session_items[first_index + 1 :]:
            for first_candidate_index, first_candidate in enumerate(first_candidates):
                for second_candidate_index, second_candidate in enumerate(second_candidates):
                    if not conflicts(first_candidate, second_candidate):
                        continue

                    model.add(
                        candidate_variables[first_session_id][first_candidate_index]
                        + candidate_variables[second_session_id][second_candidate_index]
                        <= 1
                    )


def _add_faculty_constraints(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
) -> None:
    """Prevent overlapping sessions assigned to the same faculty member."""

    def conflicts(
        first: SchedulingCandidate,
        second: SchedulingCandidate,
    ) -> bool:
        return (
            first.placement.session.faculty_id
            == second.placement.session.faculty_id
            and _placements_overlap(
                first.placement,
                second.placement,
            )
        )

    _add_pairwise_candidate_conflict_constraints(
        model,
        candidate_domains,
        candidate_variables,
        conflicts,
    )


def _add_academic_group_constraints(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    academic_group_parent_ids: dict[int, int | None] | None,
) -> None:
    """Prevent overlapping sessions with overlapping student populations."""

    def conflicts(
        first: SchedulingCandidate,
        second: SchedulingCandidate,
    ) -> bool:
        return academic_group_conflict(
            first.placement,
            second.placement,
            academic_group_parent_ids,
        )

    _add_pairwise_candidate_conflict_constraints(
        model,
        candidate_domains,
        candidate_variables,
        conflicts,
    )


def _add_room_constraints(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
) -> None:
    """Prevent overlapping sessions from using the same physical room."""

    def conflicts(
        first: SchedulingCandidate,
        second: SchedulingCandidate,
    ) -> bool:
        if first.room is None or second.room is None:
            return False

        return (
            first.room.id == second.room.id
            and _placements_overlap(
                first.placement,
                second.placement,
            )
        )

    _add_pairwise_candidate_conflict_constraints(
        model,
        candidate_domains,
        candidate_variables,
        conflicts,
    )


def solve(problem: SchedulingProblem) -> SolverResult:
    """Solve the hard-constraint session-placement-and-room problem using CP-SAT."""

    candidate_domains = build_scheduling_candidate_domains(problem)

    model = cp_model.CpModel()

    candidate_variables: dict[str, list[cp_model.IntVar]] = {}

    for session_id, candidates in candidate_domains.items():
        variables = [
            model.new_bool_var(
                f"{session_id}:candidate:{index}"
            )
            for index in range(len(candidates))
        ]

        model.add_exactly_one(variables)

        candidate_variables[session_id] = variables

    _add_faculty_constraints(
        model,
        candidate_domains,
        candidate_variables,
    )

    _add_academic_group_constraints(
        model,
        candidate_domains,
        candidate_variables,
        problem.timetable_input.academic_group_parent_ids,
    )

    _add_room_constraints(
        model,
        candidate_domains,
        candidate_variables,
    )

    objective = build_student_group_gap_objective(
        model,
        candidate_domains,
        candidate_variables,
        days=problem.timetable_input.days,
        periods_per_day=problem.timetable_input.periods_per_day,
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        raise RuntimeError("CP-SAT could not find a timetable")

    selected_candidates: list[SchedulingCandidate] = []

    for session_id, candidates in candidate_domains.items():
        variables = candidate_variables[session_id]

        selected_index = next(
            index
            for index, variable in enumerate(variables)
            if solver.value(variable) == 1
        )

        selected_candidates.append(candidates[selected_index])

    placements = tuple(
        candidate.placement
        for candidate in selected_candidates
    )

    room_assignments = tuple(
        RoomAssignment(
            placement=candidate.placement,
            room=candidate.room,
        )
        for candidate in selected_candidates
        if candidate.room is not None
    )

    return SolverResult(
        timetable=Timetable(
            placements=placements,
            room_assignments=room_assignments,
        ),
    )