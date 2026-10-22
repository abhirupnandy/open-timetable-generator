from __future__ import annotations

from ortools.sat.python import cp_model

from app.optimisation.faculty_workload import (
    build_faculty_workload_objective,
)


def _solve_objective(
    utilisation_values: list[tuple[str, int]],
) -> int:
    model = cp_model.CpModel()

    objective = build_faculty_workload_objective(
        model,
        faculty_utilisation_variables={
            designation: variables
            for designation, variables in _group_variables(
                model,
                utilisation_values,
            ).items()
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


def _group_variables(
    model: cp_model.CpModel,
    utilisation_values: list[tuple[str, int]],
) -> dict[str, list[cp_model.IntVar]]:
    grouped: dict[str, list[cp_model.IntVar]] = {}

    for index, (designation, utilisation) in enumerate(utilisation_values):
        variable = model.new_int_var(
            0,
            100,
            f"utilisation_{index}",
        )
        model.add(variable == utilisation)

        grouped.setdefault(designation, []).append(variable)

    return grouped


def test_equal_utilisation_has_zero_objective() -> None:
    result = _solve_objective(
        [
            ("ASSISTANT_PROFESSOR", 100),
            ("ASSISTANT_PROFESSOR", 100),
        ]
    )

    assert result == 0


def test_unequal_utilisation_has_positive_objective() -> None:
    result = _solve_objective(
        [
            ("ASSISTANT_PROFESSOR", 100),
            ("ASSISTANT_PROFESSOR", 80),
        ]
    )

    assert result > 0


def test_objective_is_symmetric() -> None:
    first = _solve_objective(
        [
            ("ASSISTANT_PROFESSOR", 100),
            ("ASSISTANT_PROFESSOR", 80),
        ]
    )

    second = _solve_objective(
        [
            ("ASSISTANT_PROFESSOR", 80),
            ("ASSISTANT_PROFESSOR", 100),
        ]
    )

    assert first == second


def test_designations_are_balanced_independently() -> None:
    result = _solve_objective(
        [
            ("ASSISTANT_PROFESSOR", 100),
            ("ASSISTANT_PROFESSOR", 80),
            ("ASSOCIATE_PROFESSOR", 100),
            ("ASSOCIATE_PROFESSOR", 100),
        ]
    )

    assert result > 0


def test_single_faculty_has_zero_objective() -> None:
    result = _solve_objective(
        [
            ("ASSISTANT_PROFESSOR", 100),
        ]
    )

    assert result == 0


def test_empty_input_has_zero_objective() -> None:
    result = _solve_objective([])

    assert result == 0