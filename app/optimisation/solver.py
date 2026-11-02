from __future__ import annotations

import time
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from app.core.timetable_config import TimetableConfig
from app.domain.diagnostics import Diagnostic, PreSolveError, run_presolve_checks
from app.domain.populations import GroupHierarchy
from app.domain.problem import SchedulingProblem
from app.domain.room_assignment import RoomAssignment
from app.domain.schedule import Timetable
from app.domain.scheduling_candidate import SchedulingCandidate
from app.domain.scheduling_candidate_domains import (
    EmptyDomainsError,
    build_scheduling_candidate_domains,
)
from app.optimisation.constraints import PenaltyTerm, apply_constraints
from app.optimisation.model_context import ModelContext, build_model_context


@dataclass(frozen=True)
class PenaltyValue:
    key: str
    kind: str
    weight: int
    value: int

    @property
    def weighted(self) -> int:
        return self.weight * self.value


@dataclass(frozen=True)
class SolverResult:
    """Result returned by the CP-SAT solver."""

    timetable: Timetable
    status: str = "UNKNOWN"
    objective_value: float | None = None
    best_bound: float | None = None
    wall_time_seconds: float = 0.0
    build_time_seconds: float = 0.0
    penalties: tuple[PenaltyValue, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    model_stats: dict[str, int] = field(default_factory=dict)

    def penalty(self, key: str) -> int | None:
        return next((item.value for item in self.penalties if item.key == key), None)


class InfeasibleTimetableError(RuntimeError):
    """CP-SAT proved the model infeasible or found no solution in time."""

    def __init__(
        self,
        status: str,
        diagnostics: list[Diagnostic],
        enabled_hard_constraints: list[str],
    ) -> None:
        self.status = status
        self.diagnostics = diagnostics
        self.enabled_hard_constraints = enabled_hard_constraints

        lines = [f"CP-SAT could not find a timetable. Status={status}"]

        if diagnostics:
            lines.append("Pre-solve diagnostics:")
            lines.extend(f"  {item}" for item in diagnostics)
        else:
            lines.append("Pre-solve diagnostics found no obvious capacity problem.")

        lines.append("Enabled optional hard constraints (candidates to relax):")
        lines.extend(f"  - {name}" for name in enabled_hard_constraints or ["(none)"])

        super().__init__("\n".join(lines))


@dataclass
class BuiltModel:
    context: ModelContext
    terms: list[PenaltyTerm]
    diagnostics: list[Diagnostic]

    @property
    def model(self) -> cp_model.CpModel:
        return self.context.model


def build_model(
    problem: SchedulingProblem,
    config: TimetableConfig | None = None,
) -> BuiltModel:
    """Run pre-solve checks and build the complete CP-SAT model."""

    config = config or TimetableConfig()
    timetable_input = problem.timetable_input

    hierarchy = GroupHierarchy(
        timetable_input.academic_group_parent_ids,
        (session.academic_group_id for session in timetable_input.sessions),
    )

    diagnostics = run_presolve_checks(timetable_input, config, hierarchy)
    errors = [item for item in diagnostics if item.severity == "error"]

    try:
        domains = build_scheduling_candidate_domains(problem, config, hierarchy=hierarchy)
    except EmptyDomainsError as exc:
        if errors:
            raise PreSolveError([*exc.diagnostics, *errors]) from exc
        raise

    if errors:
        raise PreSolveError(diagnostics)

    context = build_model_context(problem, domains, config, hierarchy)
    terms = apply_constraints(context)

    objective_terms = [term.weight * term.var for term in terms if term.weight]

    if objective_terms:
        context.model.minimize(sum(objective_terms))

    _add_solution_hint(context)

    return BuiltModel(context=context, terms=terms, diagnostics=diagnostics)


def _add_solution_hint(context: ModelContext) -> None:
    """Warm-start from the previous timetable when one is supplied."""

    previous = context.timetable_input.previous_placements

    if not previous:
        return

    for session_id, candidates in context.domains.items():
        prior = previous.get(session_id)

        if prior is None:
            continue

        variables = context.candidate_vars[session_id]
        best: int | None = None

        for index, candidate in enumerate(candidates):
            placement = candidate.placement
            if placement.day != prior.day or placement.start_period != prior.start_period:
                continue
            room_id = candidate.room.id if candidate.room is not None else None
            if room_id == prior.room_id:
                best = index
                break
            if best is None:
                best = index

        if best is None:
            continue

        for index, variable in enumerate(variables):
            context.model.add_hint(variable, 1 if index == best else 0)


def solve(
    problem: SchedulingProblem,
    config: TimetableConfig | None = None,
) -> SolverResult:
    """Solve the timetable placement and room problem using CP-SAT."""

    config = config or TimetableConfig()

    build_start = time.perf_counter()
    built = build_model(problem, config)
    build_time = time.perf_counter() - build_start

    context = built.context

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(config.solver.max_time_seconds)
    solver.parameters.num_search_workers = config.solver.workers
    solver.parameters.log_search_progress = config.solver.log_progress

    if config.solver.random_seed is not None:
        solver.parameters.random_seed = config.solver.random_seed

    status = solver.solve(context.model)
    status_name = solver.status_name(status)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise InfeasibleTimetableError(
            status_name,
            built.diagnostics,
            config.enabled_optional_hard_constraints(),
        )

    selected: list[SchedulingCandidate] = []

    for session_id, candidates in context.domains.items():
        variables = context.candidate_vars[session_id]
        selected_index = next(
            index for index, variable in enumerate(variables) if solver.value(variable) == 1
        )
        selected.append(candidates[selected_index])

    timetable = Timetable(
        placements=tuple(candidate.placement for candidate in selected),
        room_assignments=tuple(
            RoomAssignment(placement=candidate.placement, room=candidate.room)
            for candidate in selected
            if candidate.room is not None
        ),
    )

    penalties = tuple(
        PenaltyValue(term.key, term.kind, term.weight, int(solver.value(term.var)))
        for term in built.terms
    )

    proto = context.model.proto
    has_objective = bool(built.terms) and any(term.weight for term in built.terms)

    return SolverResult(
        timetable=timetable,
        status=status_name,
        objective_value=solver.objective_value if has_objective else None,
        best_bound=solver.best_objective_bound if has_objective else None,
        wall_time_seconds=solver.wall_time,
        build_time_seconds=build_time,
        penalties=penalties,
        diagnostics=tuple(built.diagnostics),
        model_stats={
            "sessions": len(context.domains),
            "candidates": len(context.entries),
            "variables": len(proto.variables),
            "constraints": len(proto.constraints),
        },
    )
