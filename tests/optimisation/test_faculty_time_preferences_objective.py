from __future__ import annotations

import pytest
from ortools.sat.python import cp_model

from app.optimisation.faculty_time_preferences_objective import (
    build_faculty_time_preferences_objective,
)


def _solve_objective(
    *,
    preference: str,
    selected: list[bool],
) -> int:
    model = cp_model.CpModel()

    variables = [
        model.new_bool_var(f"candidate_{index}")
        for index in range(len(selected))
    ]

    for variable, value in zip(variables, selected, strict=True):
        model.add(variable == int(value))

    objective = build_faculty_time_preferences_objective(
        model,
        faculty_time_preference_variables={
            (1, preference): variables,
        },
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    )

    return solver.value(objective)


def test_selected_non_preferred_period_is_penalised() -> None:
    penalty = _solve_objective(
        preference="MORNING",
        selected=[True],
    )

    assert penalty == 1


def test_selected_preferred_period_has_no_penalty() -> None:
    # The objective receives only non-preferred-period variables.
    # An empty list therefore represents no violation.
    penalty = _solve_objective(
        preference="MORNING",
        selected=[],
    )

    assert penalty == 0


def test_any_preference_has_no_penalty() -> None:
    penalty = _solve_objective(
        preference="ANY",
        selected=[],
    )

    assert penalty == 0


def test_multiple_non_preferred_periods_are_counted() -> None:
    penalty = _solve_objective(
        preference="MORNING",
        selected=[True, True, False, True],
    )

    assert penalty == 3


def test_evening_preference_counts_selected_violations() -> None:
    penalty = _solve_objective(
        preference="EVENING",
        selected=[True, True],
    )

    assert penalty == 2


def test_multiple_faculty_preferences_are_combined() -> None:
    model = cp_model.CpModel()

    faculty_one = [
        model.new_bool_var("faculty_1_candidate_1"),
        model.new_bool_var("faculty_1_candidate_2"),
    ]
    faculty_two = [
        model.new_bool_var("faculty_2_candidate_1"),
    ]

    model.add(faculty_one[0] == 1)
    model.add(faculty_one[1] == 0)
    model.add(faculty_two[0] == 1)

    objective = build_faculty_time_preferences_objective(
        model,
        faculty_time_preference_variables={
            (1, "MORNING"): faculty_one,
            (2, "EVENING"): faculty_two,
        },
    )

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    )
    assert solver.value(objective) == 2


def test_no_variables_produces_zero_penalty() -> None:
    model = cp_model.CpModel()

    objective = build_faculty_time_preferences_objective(
        model,
        faculty_time_preference_variables={},
    )

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    )
    assert solver.value(objective) == 0


def test_unknown_preference_raises_value_error() -> None:
    model = cp_model.CpModel()
    variable = model.new_bool_var("candidate")

    with pytest.raises(
        ValueError,
        match="Unknown faculty time preference",
    ):
        build_faculty_time_preferences_objective(
            model,
            faculty_time_preference_variables={
                (1, "INVALID"): [variable],
            },
        )