from __future__ import annotations

from ortools.sat.python import cp_model

from app.optimisation.theory_sessions import (
    build_theory_sessions_objective,
)


def test_two_theory_sessions_have_zero_penalty() -> None:
    model = cp_model.CpModel()

    session_variables = [
        model.new_bool_var(f"session_{index}")
        for index in range(2)
    ]

    objective = build_theory_sessions_objective(
        model,
        theory_session_variables={
            (1, 1): session_variables,
        },
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 0


def test_three_theory_sessions_have_one_penalty() -> None:
    model = cp_model.CpModel()

    session_variables = [
        model.new_bool_var(f"session_{index}")
        for index in range(3)
    ]

    for variable in session_variables:
        model.add(variable == 1)

    objective = build_theory_sessions_objective(
        model,
        theory_session_variables={
            (1, 1): session_variables,
        },
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 1


def test_four_theory_sessions_have_two_penalty() -> None:
    model = cp_model.CpModel()

    session_variables = [
        model.new_bool_var(f"session_{index}")
        for index in range(4)
    ]

    for variable in session_variables:
        model.add(variable == 1)

    objective = build_theory_sessions_objective(
        model,
        theory_session_variables={
            (1, 1): session_variables,
        },
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 2


def test_penalty_is_calculated_independently_for_each_faculty_and_day() -> None:
    model = cp_model.CpModel()

    monday_variables = [
        model.new_bool_var(f"monday_{index}")
        for index in range(3)
    ]
    tuesday_variables = [
        model.new_bool_var(f"tuesday_{index}")
        for index in range(4)
    ]

    for variable in monday_variables + tuesday_variables:
        model.add(variable == 1)

    objective = build_theory_sessions_objective(
        model,
        theory_session_variables={
            (1, 1): monday_variables,
            (1, 2): tuesday_variables,
        },
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 3


def test_unselected_theory_sessions_do_not_contribute_to_penalty() -> None:
    model = cp_model.CpModel()

    session_variables = [
        model.new_bool_var(f"session_{index}")
        for index in range(4)
    ]

    model.add(session_variables[0] == 1)
    model.add(session_variables[1] == 1)
    model.add(session_variables[2] == 0)
    model.add(session_variables[3] == 0)

    objective = build_theory_sessions_objective(
        model,
        theory_session_variables={
            (1, 1): session_variables,
        },
    )

    model.minimize(objective)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    assert solver.value(objective) == 0
