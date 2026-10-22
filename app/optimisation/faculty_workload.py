from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from ortools.sat.python import cp_model

FACULTY_TEACHING_CAPACITY = {
    "ASSISTANT_PROFESSOR": 13,
    "ASSOCIATE_PROFESSOR": 11,
    "PROFESSOR": 9,
    "PHD_SCHOLAR": 8,
}


def calculate_s2_penalty(
    faculty: Iterable[object],
) -> int:
    """
    Calculate the S2 faculty workload-balance penalty.

    Faculty are grouped by designation. Within each designation,
    teaching utilisation is compared after normalising each faculty
    member's teaching hours by their designation-specific maximum.

    The penalty is the sum of pairwise absolute utilisation
    differences within each designation, scaled by 100.
    """
    utilisation_by_designation: dict[str, list[float]] = defaultdict(list)

    for member in faculty:
        designation = member.designation
        teaching_hours = member.teaching_hours

        if teaching_hours < 0:
            raise ValueError("teaching_hours cannot be negative")

        try:
            capacity = FACULTY_TEACHING_CAPACITY[designation]
        except KeyError as exc:
            raise ValueError(
                f"Unknown faculty designation: {designation!r}"
            ) from exc

        utilisation = teaching_hours / capacity
        utilisation_by_designation[designation].append(utilisation)

    penalty = 0.0

    for utilisations in utilisation_by_designation.values():
        for index, utilisation in enumerate(utilisations):
            for other in utilisations[index + 1:]:
                penalty += abs(utilisation - other)

    return round(penalty * 100)


def build_faculty_workload_objective(
    model: cp_model.CpModel,
    *,
    faculty_utilisation_variables: dict[
        str,
        list[cp_model.IntVar],
    ],
) -> cp_model.IntVar:
    """
    Build the S2 faculty workload-balance objective.

    Each utilisation variable is represented on a 0-100 scale:

        0   = 0% utilisation
        100 = 100% utilisation

    Faculty are balanced independently within each designation.

    For every pair of faculty members in the same designation,
    the absolute difference in utilisation is penalised.

    Therefore:

        100%, 100% -> 0
        100%, 80%  -> 20
    """
    objective_terms: list[cp_model.IntVar] = []

    for designation, utilisation_variables in (
        faculty_utilisation_variables.items()
    ):
        for index, first in enumerate(utilisation_variables):
            for other_index in range(
                index + 1,
                len(utilisation_variables),
            ):
                second = utilisation_variables[other_index]

                difference = model.new_int_var(
                    0,
                    100,
                    f"s2_difference_{designation}_{index}_{other_index}",
                )

                model.add_abs_equality(
                    difference,
                    first - second,
                )

                objective_terms.append(difference)

    objective = model.new_int_var(
        0,
        max(
            0,
            len(objective_terms) * 100,
        ),
        "s2_faculty_workload_penalty",
    )

    if objective_terms:
        model.add(objective == sum(objective_terms))
    else:
        model.add(objective == 0)

    return objective