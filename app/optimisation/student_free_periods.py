from __future__ import annotations

from collections import defaultdict

from ortools.sat.python import cp_model

from app.domain.calendar import Day
from app.domain.schedule import Timetable

MINIMUM_FREE_PERIODS_PER_DAY = 2


def calculate_student_free_period_penalty(
    timetable: Timetable,
    *,
    periods_per_day: int,
) -> int:
    """
    Calculate the S14 student free-period penalty.

    Each academic group should have at least two free timetable
    periods per day.

    Penalty per group/day:

        max(0, 2 - number_of_free_periods)

    Free periods do not need to be consecutive.

    Lunch is not represented in the timetable period model and
    therefore does not count as a free period.
    """
    if periods_per_day <= 0:
        raise ValueError("periods_per_day must be positive")

    occupied_periods: dict[tuple[int, Day], set[int]] = defaultdict(set)

    for placement in timetable.placements:
        group_id = placement.session.academic_group_id

        for period in placement.occupied_periods:
            occupied_periods[(group_id, placement.day)].add(period)

    total_penalty = 0

    for periods in occupied_periods.values():
        free_periods = periods_per_day - len(periods)

        total_penalty += max(
            0,
            MINIMUM_FREE_PERIODS_PER_DAY - free_periods,
        )

    return total_penalty


def build_student_free_period_objective(
    model: cp_model.CpModel,
    *,
    occupied_period_variables: dict[tuple[int, int], list[cp_model.IntVar]],
    periods_per_day: int,
) -> cp_model.IntVar:
    """
    Build the S14 CP-SAT objective.

    ``occupied_period_variables`` maps:

        (academic_group_id, day_index) -> occupied-period variables

    Each occupied-period variable represents whether that academic
    group is occupied during a particular timetable period.

    The penalty is:

        max(0, 2 - free_periods)

    Since:

        free_periods = periods_per_day - occupied_periods

    this is equivalent to:

        max(0, occupied_periods - (periods_per_day - 2))

    Therefore:

        8 occupied periods -> 2 penalty
        7 occupied periods -> 1 penalty
        6 or fewer occupied periods -> 0 penalty
    """
    if periods_per_day <= 0:
        raise ValueError("periods_per_day must be positive")

    objective_terms: list[cp_model.IntVar] = []

    threshold = periods_per_day - MINIMUM_FREE_PERIODS_PER_DAY

    for (group_id, day_index), occupied_variables in occupied_period_variables.items():
        occupied_count = model.new_int_var(
            0,
            periods_per_day,
            f"s14_occupied_{group_id}_{day_index}",
        )

        if occupied_variables:
            model.add(occupied_count == sum(occupied_variables))
        else:
            model.add(occupied_count == 0)

        penalty = model.new_int_var(
            0,
            MINIMUM_FREE_PERIODS_PER_DAY,
            f"s14_penalty_{group_id}_{day_index}",
        )

        model.add_max_equality(
            penalty,
            [
                occupied_count - threshold,
                0,
            ],
        )

        objective_terms.append(penalty)

    objective = model.new_int_var(
        0,
        max(
            0,
            len(occupied_period_variables)
            * MINIMUM_FREE_PERIODS_PER_DAY,
        ),
        "s14_student_free_period_penalty",
    )

    if objective_terms:
        model.add(objective == sum(objective_terms))
    else:
        model.add(objective == 0)

    return objective