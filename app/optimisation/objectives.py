from __future__ import annotations

from ortools.sat.python import cp_model

from app.domain.scheduling_candidate import SchedulingCandidate


def _add_occupied_period_variable(
    model: cp_model.CpModel,
    *,
    group_id: int,
    day,
    period: int,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
) -> cp_model.IntVar:
    """Create a Boolean indicating whether a group occupies a period."""

    occupied = model.new_bool_var(
        f"group:{group_id}:day:{day.value}:period:{period}:occupied"
    )

    covering_variables: list[cp_model.IntVar] = []

    for session_id, candidates in candidate_domains.items():
        for index, candidate in enumerate(candidates):
            session = candidate.placement.session

            if session.academic_group_id != group_id:
                continue

            placement = candidate.placement

            if placement.day != day:
                continue

            if period not in placement.occupied_periods:
                continue

            covering_variables.append(candidate_variables[session_id][index])

    if covering_variables:
        model.add(occupied == sum(covering_variables))
    else:
        model.add(occupied == 0)

    return occupied


def _add_prefix_variable(
    model: cp_model.CpModel,
    *,
    occupied_variables: tuple[cp_model.IntVar, ...],
    end_period: int,
    group_id: int,
    day,
) -> cp_model.IntVar:
    """Create a Boolean indicating occupancy before the current period."""

    prefix = model.new_bool_var(
        f"group:{group_id}:day:{day.value}:before:{end_period + 1}"
    )

    previous_periods = occupied_variables[:end_period]

    if previous_periods:
        model.add_max_equality(prefix, list(previous_periods))
    else:
        model.add(prefix == 0)

    return prefix


def _add_suffix_variable(
    model: cp_model.CpModel,
    *,
    occupied_variables: tuple[cp_model.IntVar, ...],
    start_period: int,
    group_id: int,
    day,
) -> cp_model.IntVar:
    """Create a Boolean indicating occupancy after the current period."""

    suffix = model.new_bool_var(
        f"group:{group_id}:day:{day.value}:after:{start_period + 1}"
    )

    following_periods = occupied_variables[start_period:]

    if following_periods:
        model.add_max_equality(suffix, list(following_periods))
    else:
        model.add(suffix == 0)

    return suffix


def _add_gap_variable(
    model: cp_model.CpModel,
    *,
    occupied: cp_model.IntVar,
    prefix: cp_model.IntVar,
    suffix: cp_model.IntVar,
    group_id: int,
    day,
    period: int,
) -> cp_model.IntVar:
    """Create a Boolean indicating an internal free period."""

    gap = model.new_bool_var(
        f"group:{group_id}:day:{day.value}:period:{period}:gap"
    )

    model.add_bool_and(
        [
            prefix,
            suffix,
            occupied.Not(),
        ]
    ).only_enforce_if(gap)

    model.add_bool_or(
        [
            prefix.Not(),
            suffix.Not(),
            occupied,
        ]
    ).only_enforce_if(gap.Not())

    return gap


def build_student_group_gap_objective(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    *,
    days,
    periods_per_day: int,
) -> cp_model.LinearExpr:
    """Return the total number of internal group timetable gaps."""

    group_ids = {
        candidate.placement.session.academic_group_id
        for candidates in candidate_domains.values()
        for candidate in candidates
    }

    gap_variables: list[cp_model.IntVar] = []

    for group_id in sorted(group_ids):
        for day in days:
            occupied_variables = tuple(
                _add_occupied_period_variable(
                    model,
                    group_id=group_id,
                    day=day,
                    period=period,
                    candidate_domains=candidate_domains,
                    candidate_variables=candidate_variables,
                )
                for period in range(1, periods_per_day + 1)
            )

            for period in range(1, periods_per_day + 1):
                prefix = _add_prefix_variable(
                    model,
                    occupied_variables=occupied_variables,
                    end_period=period - 1,
                    group_id=group_id,
                    day=day,
                )

                suffix = _add_suffix_variable(
                    model,
                    occupied_variables=occupied_variables,
                    start_period=period,
                    group_id=group_id,
                    day=day,
                )

                gap_variables.append(
                    _add_gap_variable(
                        model,
                        occupied=occupied_variables[period - 1],
                        prefix=prefix,
                        suffix=suffix,
                        group_id=group_id,
                        day=day,
                        period=period,
                    )
                )

    return sum(gap_variables)