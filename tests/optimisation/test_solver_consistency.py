"""Cross-checks between the CP-SAT model and the independent calculators."""

from __future__ import annotations

import random

import pytest

from app.db.models.subject import SubjectType
from app.domain.calendar import Day
from app.domain.room import RoomType, SchedulingRoom
from app.domain.timetable import PreviousPlacement
from app.domain.validator import validate_timetable
from app.optimisation.constraints import SOFT_BUILDERS
from app.optimisation.penalties import calculate_all_penalties
from app.optimisation.solver import build_model, solve
from tests.optimisation import helpers as h

DAYS = (Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY)


def _random_problem(seed: int):
    rng = random.Random(seed)
    parents = {1: None, 2: None, 11: 1, 12: 1, 21: 2, 22: 2}
    sessions = []

    for parent in (1, 2):
        for subject in range(3):
            sessions += h.sessions_of(
                rng.randint(1, 3),
                group=parent,
                faculty=rng.randint(1, 4),
                subject=parent * 10 + subject,
                mode=rng.choice(["IN_PERSON", "IN_PERSON", "EITHER", "ONLINE"]),
            )
        for batch in (parent * 10 + 1, parent * 10 + 2):
            sessions += h.sessions_of(
                1,
                group=batch,
                faculty=rng.randint(5, 6),
                subject=batch * 10,
                duration=2,
                room_type="COMPUTER_LAB",
                subject_type=SubjectType.LAB,
            )

    rooms = [
        SchedulingRoom(1, RoomType.CLASSROOM, 60),
        SchedulingRoom(2, RoomType.CLASSROOM, 100),
        SchedulingRoom(3, RoomType.COMPUTER_LAB, 30),
        SchedulingRoom(4, RoomType.COMPUTER_LAB, 40),
    ]

    previous = {
        item.id: PreviousPlacement(rng.choice(DAYS), rng.randint(1, 5))
        for item in rng.sample(sessions, k=len(sessions) // 2)
    }

    return h.problem(
        sessions,
        days=DAYS,
        periods=6,
        rooms=rooms,
        lunch_after_period=3,
        academic_group_parent_ids=parents,
        academic_group_capacities={1: 50, 2: 50, 11: 25, 12: 25, 21: 25, 22: 25},
        faculty_designations={index: "ASSISTANT_PROFESSOR" for index in range(1, 7)},
        faculty_time_preferences={1: "MORNING", 2: "AFTERNOON", 3: "EVENING"},
        faculty_preferred_day_off={4: Day.TUESDAY},
        previous_placements=previous,
    )


def _everything_on():
    data = h.base_config(max_time_seconds=5)
    for key in data["soft"]:
        data["soft"][key].update({"enabled": True, "weight": 1 + len(key) % 7})
    data["soft"]["faculty_time_preference"]["ranges"] = {
        "MORNING": [1, 2, 3],
        "AFTERNOON": [4, 5, 6],
        "EVENING": [5, 6],
    }
    data["soft"]["avoid_periods"]["rules"] = [
        {"period": 6, "penalty": 2},
        {"period": 1, "penalty": 1, "subject_types": ["LAB"]},
    ]
    data["soft"]["stability_vs_previous"]["room_change_penalty"] = 1
    data["soft"]["faculty_daily_load"]["max_periods"] = 3
    data["constraints"]["no_session_across_lunch"].update({"mode": "soft", "weight": 3})
    data["constraints"]["faculty_max_consecutive"].update(
        {"mode": "soft", "weight": 2, "max_periods": 2}
    )
    data["constraints"]["student_max_consecutive"].update(
        {"mode": "soft", "weight": 2, "max_periods": 2}
    )
    data["hard"]["faculty_daily_span"]["enabled"] = True
    data["hard"]["faculty_weekly_cap"]["enabled"] = True
    return h.TimetableConfig.model_validate(data)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_solver_penalties_match_independent_calculators(seed):
    problem = _random_problem(seed)
    config = _everything_on()

    result = solve(problem, config)
    calculated = calculate_all_penalties(result.timetable, problem.timetable_input, config)

    reported = {item.key: item.value for item in result.penalties}
    assert set(reported) == set(calculated)  # every constraint is active here

    mismatches = {
        key: (reported[key], calculated[key])
        for key in reported
        if reported[key] != calculated[key]
    }
    assert not mismatches

    validation = validate_timetable(
        result.timetable, timetable_input=problem.timetable_input, config=config
    )
    assert validation.is_valid, (validation.conflicts, validation.violations)


def _var_names(config, problem=None):
    built = build_model(problem or _random_problem(1), config)
    return [variable.name for variable in built.model.proto.variables]


def test_disabled_constraints_add_no_variables():
    names = _var_names(h.config_with())
    assert not [name for name in names if name.startswith("pen:")]

    baseline = len(names)

    for key in SOFT_BUILDERS:
        enabled = h.config_with(("soft", key, {"enabled": True, "weight": 1}))
        enabled_names = _var_names(enabled)
        assert any(name.startswith(f"pen:{key}") for name in enabled_names), key
        # Nothing belonging to any *other* soft constraint appears.
        others = [
            name
            for name in enabled_names
            if name.startswith("pen:") and not name.startswith(f"pen:{key}")
        ]
        assert not others, (key, others[:3])
        assert len(enabled_names) >= baseline


def test_flexible_off_adds_no_variables():
    for key in ("no_session_across_lunch", "faculty_max_consecutive", "student_max_consecutive"):
        names = _var_names(h.config_with(("constraints", key, {"mode": "off"})))
        assert not any(name.startswith(f"pen:{key}") for name in names)
        soft_names = _var_names(h.config_with(("constraints", key, {"mode": "soft", "weight": 1})))
        assert any(name.startswith(f"pen:{key}") for name in soft_names)


def test_all_optional_constraints_off_is_feasible():
    problem = _random_problem(2)
    result = solve(problem, h.config_with())
    assert len(result.timetable.placements) == len(problem.sessions)
    assert result.penalties == ()
