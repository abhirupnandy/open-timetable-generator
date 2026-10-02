from __future__ import annotations

from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.domain.candidate_domains import build_candidate_domains
from app.domain.placement import SessionPlacement
from app.domain.problem import SchedulingProblem
from app.domain.schedule import Timetable


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
    candidate_domains: dict[str, tuple[SessionPlacement, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    conflicts,
) -> None:
    """Prevent incompatible candidate placements from being selected together."""

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
    candidate_domains: dict[str, tuple[SessionPlacement, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
) -> None:
    """Prevent overlapping sessions assigned to the same faculty member."""

    def conflicts(
        first: SessionPlacement,
        second: SessionPlacement,
    ) -> bool:
        return (
            first.session.faculty_id == second.session.faculty_id
            and _placements_overlap(first, second)
        )

    _add_pairwise_candidate_conflict_constraints(
        model,
        candidate_domains,
        candidate_variables,
        conflicts,
    )


def _add_academic_group_constraints(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SessionPlacement, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
) -> None:
    """Prevent overlapping sessions assigned to the same academic group."""

    def conflicts(
        first: SessionPlacement,
        second: SessionPlacement,
    ) -> bool:
        return (
            first.session.academic_group_id == second.session.academic_group_id
            and _placements_overlap(first, second)
        )

    _add_pairwise_candidate_conflict_constraints(
        model,
        candidate_domains,
        candidate_variables,
        conflicts,
    )


def solve(problem: SchedulingProblem) -> SolverResult:
    """Solve the minimal session-placement problem using CP-SAT."""

    candidate_domains = build_candidate_domains(problem)

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
    )

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        raise RuntimeError("CP-SAT could not find a timetable")

    placements: list[SessionPlacement] = []

    for session_id, candidates in candidate_domains.items():
        variables = candidate_variables[session_id]

        selected_index = next(
            index
            for index, variable in enumerate(variables)
            if solver.value(variable) == 1
        )

        placements.append(candidates[selected_index])

    return SolverResult(
        timetable=Timetable(
            placements=tuple(placements),
        ),
    )