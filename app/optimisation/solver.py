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
from app.optimisation.faculty_time_preferences_objective import (
    build_faculty_time_preferences_objective,
)
from app.optimisation.faculty_workload import (
    build_faculty_workload_objective,
)
from app.optimisation.objectives import (
    build_student_group_gap_objective,
    build_subject_spreading_objective,
)
from app.optimisation.student_free_periods import (
    build_student_free_period_objective,
)
from app.optimisation.theory_sessions import (
    build_theory_sessions_objective,
)


@dataclass(frozen=True)
class SolverResult:
    """Result returned by the CP-SAT solver."""

    timetable: Timetable


# Faculty weekly teaching-hour capacity.
#
# Each timetable period is exactly one hour.
#
# Professor:
#     10 total workload hours - 1 hour TREP = 9 teaching hours
#
# Associate Professor:
#     12 total workload hours - 1 hour TREP = 11 teaching hours
#
# Assistant Professor:
#     14 total workload hours - 1 hour TREP = 13 teaching hours
#
# PhD Scholar:
#     8 teaching hours
FACULTY_TEACHING_CAPACITY_HOURS: dict[str, int] = {
    "PROFESSOR": 9,
    "ASSOCIATE_PROFESSOR": 11,
    "ASSISTANT_PROFESSOR": 13,
    "PHD_SCHOLAR": 8,
}


# Maximum wall-clock span from the start of the first class
# to the end of the last class for a faculty member on one day.
FACULTY_MAX_DAILY_SPAN_MINUTES = 8 * 60


# Soft-objective weights.
#
# Higher weight means that CP-SAT gives the corresponding
# objective greater importance when minimizing the combined
# objective.
S1_STUDENT_GROUP_GAP_WEIGHT = 100
S14_STUDENT_FREE_PERIOD_WEIGHT = 90
S4_SUBJECT_SPREADING_WEIGHT = 80
S2_FACULTY_WORKLOAD_WEIGHT = 70
S11_THEORY_SESSIONS_WEIGHT = 60
S3_FACULTY_TIME_PREFERENCE_WEIGHT = 50


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
        for second_session_id, second_candidates in session_items[
            first_index + 1 :
        ]:
            for first_candidate_index, first_candidate in enumerate(
                first_candidates
            ):
                for second_candidate_index, second_candidate in enumerate(
                    second_candidates
                ):
                    if not conflicts(first_candidate, second_candidate):
                        continue

                    model.add(
                        candidate_variables[first_session_id][
                            first_candidate_index
                        ]
                        + candidate_variables[second_session_id][
                            second_candidate_index
                        ]
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


def _add_faculty_daily_span_constraints(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
) -> None:
    """
    Prevent a faculty member's classes on one day from spanning
    more than eight wall-clock hours.

    The span is measured from the start of the earliest class
    to the end of the latest class.

    Breaks between classes count toward the span.
    """

    def conflicts(
        first: SchedulingCandidate,
        second: SchedulingCandidate,
    ) -> bool:
        first_placement = first.placement
        second_placement = second.placement

        if (
            first_placement.session.faculty_id
            != second_placement.session.faculty_id
        ):
            return False

        if first_placement.day != second_placement.day:
            return False

        earliest_start = min(
            first_placement.start_time_minutes,
            second_placement.start_time_minutes,
        )

        latest_end = max(
            first_placement.end_time_minutes,
            second_placement.end_time_minutes,
        )

        return (
            latest_end - earliest_start
            > FACULTY_MAX_DAILY_SPAN_MINUTES
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


def _add_faculty_workload_constraints(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    faculty_designations: dict[int, str] | None,
) -> None:
    """
    Limit each faculty member's total scheduled teaching hours per week.

    Each timetable period represents exactly one teaching hour.

    Professor:
        10 total hours - 1 hour TREP = 9 teaching hours

    Associate Professor:
        12 total hours - 1 hour TREP = 11 teaching hours

    Assistant Professor:
        14 total hours - 1 hour TREP = 13 teaching hours

    PhD Scholar:
        8 teaching hours
    """

    if faculty_designations is None:
        return

    faculty_terms: dict[int, list[cp_model.LinearExpr]] = {}

    for session_id, candidates in candidate_domains.items():
        variables = candidate_variables[session_id]

        if not candidates:
            continue

        faculty_id = candidates[0].placement.session.faculty_id

        for candidate_index, candidate in enumerate(candidates):
            variable = variables[candidate_index]
            duration = candidate.placement.session.duration_periods

            faculty_terms.setdefault(faculty_id, []).append(
                duration * variable
            )

    for faculty_id, terms in faculty_terms.items():
        designation = faculty_designations.get(faculty_id)

        if designation is None:
            continue

        capacity = FACULTY_TEACHING_CAPACITY_HOURS.get(designation)

        if capacity is None:
            raise ValueError(
                f"Unsupported faculty designation for faculty "
                f"{faculty_id}: {designation!r}"
            )

        model.add(sum(terms) <= capacity)


def _build_faculty_utilisation_variables(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    faculty_designations: dict[int, str] | None,
) -> dict[str, list[cp_model.IntVar]]:
    """
    Build S2 faculty utilisation variables.

    Each faculty member gets an integer utilisation variable on a
    0-100 scale.

    For example:

        13 / 13 teaching hours -> 100
        10 / 13 teaching hours -> 76
        11 / 13 teaching hours -> 84

    Faculty are returned grouped by designation because S2 balances
    utilisation independently within each designation.
    """

    if faculty_designations is None:
        return {}

    faculty_terms: dict[int, list[cp_model.LinearExpr]] = {}

    for session_id, candidates in candidate_domains.items():
        variables = candidate_variables[session_id]

        if not candidates:
            continue

        faculty_id = candidates[0].placement.session.faculty_id

        for candidate_index, candidate in enumerate(candidates):
            variable = variables[candidate_index]
            duration = candidate.placement.session.duration_periods

            faculty_terms.setdefault(faculty_id, []).append(
                duration * variable
            )

    utilisation_by_designation: dict[str, list[cp_model.IntVar]] = {}

    for faculty_id, designation in faculty_designations.items():
        capacity = FACULTY_TEACHING_CAPACITY_HOURS.get(designation)

        if capacity is None:
            raise ValueError(
                f"Unsupported faculty designation for faculty "
                f"{faculty_id}: {designation!r}"
            )

        terms = faculty_terms.get(faculty_id, [])

        teaching_hours = model.new_int_var(
            0,
            capacity,
            f"s2_teaching_hours_{faculty_id}",
        )

        if terms:
            model.add(teaching_hours == sum(terms))
        else:
            model.add(teaching_hours == 0)

        utilisation = model.new_int_var(
            0,
            100,
            f"s2_utilisation_{faculty_id}",
        )

        # Integer percentage utilisation.
        #
        # utilisation = floor(
        #     teaching_hours * 100 / capacity
        # )
        #
        # The lower-bound constraint gives the floor relationship,
        # while the upper bound prevents the value from exceeding
        # the actual utilisation percentage.
        model.add(
            utilisation * capacity
            <= teaching_hours * 100
        )

        model.add(
            (utilisation + 1) * capacity
            > teaching_hours * 100
        )

        utilisation_by_designation.setdefault(
            designation,
            [],
        ).append(utilisation)

    return utilisation_by_designation


def _build_student_free_period_variables(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    *,
    days,
    periods_per_day: int,
) -> dict[tuple[int, int], list[cp_model.IntVar]]:
    """
    Build occupied-period variables for S14.

    The returned mapping contains one Boolean variable for each
    academic-group/day/period combination.

    A variable is 1 when the corresponding academic group is
    occupied during that timetable period.

    Multi-period sessions mark every period they occupy.
    """

    occupied_candidate_terms: dict[
        tuple[int, int, int],
        list[cp_model.IntVar],
    ] = {}

    day_to_index = {
        day: index
        for index, day in enumerate(days)
    }

    for session_id, candidates in candidate_domains.items():
        variables = candidate_variables[session_id]

        for candidate_index, candidate in enumerate(candidates):
            variable = variables[candidate_index]
            placement = candidate.placement
            group_id = placement.session.academic_group_id
            day_index = day_to_index[placement.day]

            for period in placement.occupied_periods:
                key = (group_id, day_index, period)

                occupied_candidate_terms.setdefault(key, []).append(
                    variable
                )

    occupied_period_variables: dict[
        tuple[int, int],
        list[cp_model.IntVar],
    ] = {}

    group_day_keys = {
        (group_id, day_index)
        for group_id, day_index, _ in occupied_candidate_terms
    }

    for group_id, day_index in sorted(group_day_keys):
        period_variables: list[cp_model.IntVar] = []

        for period in range(1, periods_per_day + 1):
            key = (group_id, day_index, period)
            terms = occupied_candidate_terms.get(key, [])

            occupied = model.new_bool_var(
                f"s14_occupied_{group_id}_{day_index}_{period}"
            )

            if terms:
                model.add_max_equality(occupied, terms)
            else:
                model.add(occupied == 0)

            period_variables.append(occupied)

        occupied_period_variables[(group_id, day_index)] = period_variables

    return occupied_period_variables


def _build_theory_session_variables(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    *,
    days,
) -> dict[tuple[int, int], list[cp_model.IntVar]]:
    """
    Build candidate-variable groups for S11.

    Each key identifies:

        (faculty_id, day_index)

    Only LECTURE candidates are included. LAB and TUTORIAL
    candidates therefore do not contribute to the S11 objective.
    """

    day_to_index = {
        day: index
        for index, day in enumerate(days)
    }

    theory_session_variables: dict[
        tuple[int, int],
        list[cp_model.IntVar],
    ] = {}

    for session_id, candidates in candidate_domains.items():
        variables = candidate_variables[session_id]

        for candidate_index, candidate in enumerate(candidates):
            session = candidate.placement.session

            if (
                session.subject_type is None
                or session.subject_type.value != "LECTURE"
            ):
                continue

            faculty_id = session.faculty_id
            day_index = day_to_index[candidate.placement.day]

            key = (faculty_id, day_index)

            theory_session_variables.setdefault(key, []).append(
                variables[candidate_index]
            )

    return theory_session_variables


def _build_faculty_time_preference_variables(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    *,
    faculty_time_preferences: dict[int, str] | None,
) -> dict[tuple[int, str], list[cp_model.IntVar]]:
    """
    Build candidate variables for the S3 faculty time-preference objective.

    Only occupied periods outside the faculty member's preferred time
    range are included.

    Preference ranges:

        ANY:
            No penalty.

        MORNING:
            P1-P4 preferred; P5-P8 penalised.

        AFTERNOON:
            P5-P8 preferred; P1-P4 penalised.

        EVENING:
            P7-P8 preferred; P1-P6 penalised.

    A multi-period candidate contributes its candidate variable once
    for each non-preferred occupied period.
    """

    if faculty_time_preferences is None:
        return {}

    preferred_periods = {
        "ANY": frozenset(range(1, 9)),
        "MORNING": frozenset({1, 2, 3, 4}),
        "AFTERNOON": frozenset({5, 6, 7, 8}),
        "EVENING": frozenset({7, 8}),
    }

    preference_variables: dict[
        tuple[int, str],
        list[cp_model.IntVar],
    ] = {}

    for session_id, candidates in candidate_domains.items():
        variables = candidate_variables[session_id]

        for candidate_index, candidate in enumerate(candidates):
            session = candidate.placement.session
            faculty_id = session.faculty_id

            preference = faculty_time_preferences.get(
                faculty_id,
                "ANY",
            )

            if preference not in preferred_periods:
                raise ValueError(
                    f"Unknown faculty time preference: {preference!r}"
                )

            preferred = preferred_periods[preference]

            for period in candidate.placement.occupied_periods:
                if period in preferred:
                    continue

                key = (faculty_id, preference)

                preference_variables.setdefault(
                    key,
                    [],
                ).append(
                    variables[candidate_index]
                )

    return preference_variables


def solve(problem: SchedulingProblem) -> SolverResult:
    """Solve the timetable placement and room problem using CP-SAT."""

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

    # 1. Same faculty cannot teach overlapping sessions.
    _add_faculty_constraints(
        model,
        candidate_domains,
        candidate_variables,
    )

    # 2. A faculty member's daily wall-clock span cannot exceed 8 hours.
    _add_faculty_daily_span_constraints(
        model,
        candidate_domains,
        candidate_variables,
    )

    # 3. Parent groups and their batches cannot overlap.
    #
    # Sibling batches remain independent.
    _add_academic_group_constraints(
        model,
        candidate_domains,
        candidate_variables,
        problem.timetable_input.academic_group_parent_ids,
    )

    # 4. A physical room cannot host overlapping sessions.
    _add_room_constraints(
        model,
        candidate_domains,
        candidate_variables,
    )

    # 5. Faculty weekly teaching-hour limits.
    _add_faculty_workload_constraints(
        model,
        candidate_domains,
        candidate_variables,
        problem.timetable_input.faculty_designations,
    )

    # ------------------------------------------------------------------
    # Soft objectives
    # ------------------------------------------------------------------

    # S1: minimize gaps inside each academic group's daily schedule.
    s1_objective = build_student_group_gap_objective(
        model,
        candidate_domains,
        candidate_variables,
        days=problem.timetable_input.days,
        periods_per_day=problem.timetable_input.periods_per_day,
    )

    # S14: each academic group should have at least two free
    # timetable periods per day.
    #
    # Lunch is not part of the timetable period model and therefore
    # is not counted here.
    occupied_period_variables = _build_student_free_period_variables(
        model,
        candidate_domains,
        candidate_variables,
        days=problem.timetable_input.days,
        periods_per_day=problem.timetable_input.periods_per_day,
    )

    s14_objective = build_student_free_period_objective(
        model,
        occupied_period_variables=occupied_period_variables,
        periods_per_day=problem.timetable_input.periods_per_day,
    )

    # S4: spread each subject across different days for each
    # academic group.
    s4_objective = build_subject_spreading_objective(
        model,
        candidate_domains,
        candidate_variables,
        days=problem.timetable_input.days,
    )

    # S2: balance faculty teaching utilisation within each
    # faculty designation.
    faculty_utilisation_variables = _build_faculty_utilisation_variables(
        model,
        candidate_domains,
        candidate_variables,
        problem.timetable_input.faculty_designations,
    )

    s2_objective = build_faculty_workload_objective(
        model,
        faculty_utilisation_variables=faculty_utilisation_variables,
    )

    # S11: avoid scheduling more than two lecture/theory sessions
    # for the same faculty member on the same day.
    theory_session_variables = _build_theory_session_variables(
        model,
        candidate_domains,
        candidate_variables,
        days=problem.timetable_input.days,
    )

    s11_objective = build_theory_sessions_objective(
        model,
        theory_session_variables=theory_session_variables,
    )

    # S3: penalise faculty sessions scheduled outside their
    # preferred time periods.
    faculty_time_preference_variables = (
        _build_faculty_time_preference_variables(
            model,
            candidate_domains,
            candidate_variables,
            faculty_time_preferences=(
                problem.timetable_input.faculty_time_preferences
            ),
        )
    )

    s3_objective = build_faculty_time_preferences_objective(
        model,
        faculty_time_preference_variables=(
            faculty_time_preference_variables
        ),
    )

    # Weighted multi-objective minimization.
    #
    # Priority:
    #
    #     S1  = 100
    #     S14 = 90
    #     S4  = 80
    #     S2  = 70
    #     S11 = 60
    #     S3  = 50
    #
    # All objectives remain active, but S1 receives the greatest
    # weight.
    objective = (
        S1_STUDENT_GROUP_GAP_WEIGHT * s1_objective
        + S14_STUDENT_FREE_PERIOD_WEIGHT * s14_objective
        + S4_SUBJECT_SPREADING_WEIGHT * s4_objective
        + S2_FACULTY_WORKLOAD_WEIGHT * s2_objective
        + S11_THEORY_SESSIONS_WEIGHT * s11_objective
        + S3_FACULTY_TIME_PREFERENCE_WEIGHT * s3_objective
    )

    # model.minimize(objective)

    solver = cp_model.CpSolver()

    # Diagnostic settings
    solver.parameters.max_time_in_seconds = 120.0
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = True

    # TEMPORARY: test feasibility without optimizing the objectives.
    # Restore model.minimize(objective) after this diagnostic.
    status = solver.solve(model)

    print(f"\nCP-SAT status: {solver.status_name(status)}")
    print(solver.response_stats())

    if status not in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
    ):
        raise RuntimeError(
            f"CP-SAT could not find a timetable. "
            f"Status={solver.status_name(status)}"
        )

    selected_candidates: list[SchedulingCandidate] = []

    for session_id, candidates in candidate_domains.items():
        variables = candidate_variables[session_id]

        selected_index = next(
            index
            for index, variable in enumerate(variables)
            if solver.value(variable) == 1
        )

        selected_candidates.append(
            candidates[selected_index]
        )

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