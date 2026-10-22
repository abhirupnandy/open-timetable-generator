from __future__ import annotations

from ortools.sat.python import cp_model

from app.optimisation.student_free_periods import (
    build_student_free_period_objective,
)


def test_two_free_periods_have_zero_penalty() -> None:
    model = cp_model.CpModel()

    occupied = [
        model.new_bool_var(f"occupied_{period}")
        for period in range(1, 7)
    ]

    for variable in occupied:
        model.add(variable == 1)

    objective = build_student_free_period_objective(
        model,
        occupied_period_variables={
            (1, 0): occupied,
        },
        periods_per_day=8,
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 0


def test_one_free_period_has_one_penalty() -> None:
    model = cp_model.CpModel()

    occupied = [
        model.new_bool_var(f"occupied_{period}")
        for period in range(1, 8)
    ]

    for variable in occupied:
        model.add(variable == 1)

    objective = build_student_free_period_objective(
        model,
        occupied_period_variables={
            (1, 0): occupied,
        },
        periods_per_day=8,
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 1


def test_zero_free_periods_have_two_penalties() -> None:
    model = cp_model.CpModel()

    occupied = [
        model.new_bool_var(f"occupied_{period}")
        for period in range(1, 9)
    ]

    for variable in occupied:
        model.add(variable == 1)

    objective = build_student_free_period_objective(
        model,
        occupied_period_variables={
            (1, 0): occupied,
        },
        periods_per_day=8,
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 2


def test_three_free_periods_have_zero_penalty() -> None:
    model = cp_model.CpModel()

    occupied = [
        model.new_bool_var(f"occupied_{period}")
        for period in range(1, 6)
    ]

    for variable in occupied:
        model.add(variable == 1)

    objective = build_student_free_period_objective(
        model,
        occupied_period_variables={
            (1, 0): occupied,
        },
        periods_per_day=8,
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 0


def test_groups_are_scored_independently() -> None:
    model = cp_model.CpModel()

    group_one = [
        model.new_bool_var(f"group1_{period}")
        for period in range(1, 8)
    ]
    group_two = [
        model.new_bool_var(f"group2_{period}")
        for period in range(1, 7)
    ]

    for variable in group_one:
        model.add(variable == 1)

    for variable in group_two:
        model.add(variable == 1)

    objective = build_student_free_period_objective(
        model,
        occupied_period_variables={
            (1, 0): group_one,
            (2, 0): group_two,
        },
        periods_per_day=8,
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    # Group 1: 1 free period -> 1 penalty.
    # Group 2: 2 free periods -> 0 penalty.
    assert solver.value(objective) == 1


def test_days_are_scored_independently() -> None:
    model = cp_model.CpModel()

    monday = [
        model.new_bool_var(f"monday_{period}")
        for period in range(1, 8)
    ]
    tuesday = [
        model.new_bool_var(f"tuesday_{period}")
        for period in range(1, 7)
    ]

    for variable in monday:
        model.add(variable == 1)

    for variable in tuesday:
        model.add(variable == 1)

    objective = build_student_free_period_objective(
        model,
        occupied_period_variables={
            (1, 0): monday,
            (1, 1): tuesday,
        },
        periods_per_day=8,
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    # Monday: 1 free period -> 1 penalty.
    # Tuesday: 2 free periods -> 0 penalty.
    assert solver.value(objective) == 1


def test_empty_group_day_has_zero_penalty() -> None:
    model = cp_model.CpModel()

    objective = build_student_free_period_objective(
        model,
        occupied_period_variables={},
        periods_per_day=8,
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 0


def test_invalid_period_count_raises() -> None:
    model = cp_model.CpModel()

    try:
        build_student_free_period_objective(
            model,
            occupied_period_variables={},
            periods_per_day=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")