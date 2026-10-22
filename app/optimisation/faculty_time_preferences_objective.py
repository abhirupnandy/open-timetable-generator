from __future__ import annotations

from ortools.sat.python import cp_model

VALID_PREFERENCES = frozenset(
    {
        "ANY",
        "MORNING",
        "AFTERNOON",
        "EVENING",
    }
)


def build_faculty_time_preferences_objective(
    model: cp_model.CpModel,
    *,
    faculty_time_preference_variables: dict[
        tuple[int, str],
        list[cp_model.IntVar],
    ],
) -> cp_model.IntVar:
    """
    Build the S3 faculty time-preference objective.

    The mapping contains only candidate Boolean variables representing
    occupied periods that fall outside the faculty member's preferred
    time range.

    A multi-period session may therefore contribute the same candidate
    variable multiple times, once for each non-preferred occupied period.

    Preference rules:

        ANY:
            No variables should be supplied.

        MORNING:
            P1-P4 preferred; P5-P8 penalised.

        AFTERNOON:
            P5-P8 preferred; P1-P4 penalised.

        EVENING:
            P7-P8 preferred; P1-P6 penalised.
    """

    for _, preference in faculty_time_preference_variables:
        if preference not in VALID_PREFERENCES:
            raise ValueError(
                f"Unknown faculty time preference: {preference!r}"
            )

    penalty_terms: list[cp_model.IntVar] = []

    for variables in faculty_time_preference_variables.values():
        penalty_terms.extend(variables)

    objective = model.new_int_var(
        0,
        len(penalty_terms),
        "s3_faculty_time_preference_penalty",
    )

    if penalty_terms:
        model.add(objective == sum(penalty_terms))
    else:
        model.add(objective == 0)

    return objective