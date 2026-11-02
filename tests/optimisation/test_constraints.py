"""Per-constraint behaviour tests.

Each scenario uses a 'decoy' preference that pulls the solution toward a
pattern the target constraint penalises. With the constraint disabled the
solver follows the decoy; enabling it (with a larger weight) must change the
chosen timetable and reduce the independently calculated penalty.
"""

from __future__ import annotations

import pytest

from app.domain.calendar import Day
from app.domain.candidates import crosses_lunch
from app.domain.timetable import PreviousPlacement
from app.optimisation.penalties import calculate_penalty
from app.optimisation.solver import solve
from tests.optimisation import helpers as h

MON, TUE, WED = Day.MONDAY, Day.TUESDAY, Day.WEDNESDAY


def _penalty(key, problem, config, result):
    return calculate_penalty(key, result.timetable, problem.timetable_input, config)


def _compare(key, problem, decoys, target):
    """Solve without/with the target constraint and return both penalties."""

    off_config = h.config_with(*decoys)
    on_config = h.config_with(*decoys, target)

    off = solve(problem, off_config)
    on = solve(problem, on_config)

    off_penalty = _penalty(key, problem, on_config, off)
    on_penalty = _penalty(key, problem, on_config, on)

    # The solver's own penalty variable must agree with the calculator.
    assert on.penalty(key) == on_penalty

    return off_penalty, on_penalty


def _soft(key, weight=10, **params):
    return ("soft", key, {"enabled": True, "weight": weight, **params})


def test_student_gaps():
    problem = h.problem([h.session(group=1, faculty=1), h.session(group=1, faculty=2)])
    off, on = _compare("student_gaps", problem, [h.avoid(2, 3)], _soft("student_gaps"))
    assert (off, on) == (2, 0)


def test_student_gaps_include_parent_sessions_for_batches():
    # Batch 2's lab plus parent 1's lecture: the batch sees the gap.
    problem = h.problem(
        [h.session(group=1, faculty=1), h.session(group=2, faculty=2)],
        academic_group_parent_ids={1: None, 2: 1},
    )
    off, on = _compare("student_gaps", problem, [h.avoid(2, 3)], _soft("student_gaps"))
    assert (off, on) == (2, 0)


def test_faculty_gaps():
    problem = h.problem([h.session(group=1, faculty=1), h.session(group=2, faculty=1)])
    off, on = _compare("faculty_gaps", problem, [h.avoid(2, 3)], _soft("faculty_gaps"))
    assert (off, on) == (2, 0)


def test_student_min_free_periods():
    problem = h.problem(
        [h.session(group=1, faculty=index) for index in range(1, 4)],
        days=(MON, TUE),
    )
    decoy = h.avoid(1, 2, 3, 4, days=["TUESDAY"])
    off, on = _compare(
        "student_min_free_periods", problem, [decoy], _soft("student_min_free_periods", min_free=2)
    )
    assert (off, on) == (1, 0)


def test_subject_spreading():
    problem = h.problem(h.sessions_of(2, group=1, faculty=1), days=(MON, TUE))
    decoy = h.avoid(1, 2, 3, 4, days=["TUESDAY"])
    off, on = _compare("subject_spreading", problem, [decoy], _soft("subject_spreading"))
    assert (off, on) == (1, 0)


def test_faculty_max_lectures_per_day():
    problem = h.problem(
        [h.session(group=index, faculty=1) for index in range(1, 4)], days=(MON, TUE)
    )
    decoy = h.avoid(1, 2, 3, 4, days=["TUESDAY"])
    off, on = _compare(
        "faculty_max_lectures_per_day",
        problem,
        [decoy],
        _soft("faculty_max_lectures_per_day", max_lectures=2),
    )
    assert (off, on) == (1, 0)


def test_faculty_time_preference():
    problem = h.problem([h.session(faculty=1)], faculty_time_preferences={1: "MORNING"})
    target = _soft(
        "faculty_time_preference",
        ranges={"MORNING": [1, 2], "AFTERNOON": [3, 4], "EVENING": [4]},
    )
    off, on = _compare("faculty_time_preference", problem, [h.avoid(1, 2)], target)
    assert (off, on) == (1, 0)


def test_avoid_periods_with_subject_type_filter():
    lab = h.session(faculty=1, subject_type=h.SubjectType.LAB)
    problem = h.problem([lab], faculty_time_preferences={1: "EVENING"})
    decoy = (
        "soft",
        "faculty_time_preference",
        {
            "enabled": True,
            "weight": 1,
            "ranges": {"MORNING": [1], "AFTERNOON": [2], "EVENING": [4]},
        },
    )
    target = (
        "soft",
        "avoid_periods",
        {"enabled": True, "weight": 10, "rules": [{"period": 4, "subject_types": ["LAB"]}]},
    )
    off, on = _compare("avoid_periods", problem, [decoy], target)
    assert (off, on) == (1, 0)


def _stability(previous, room_change_penalty=0, weight=1):
    return (
        "soft",
        "stability_vs_previous",
        {"enabled": True, "weight": weight, "room_change_penalty": room_change_penalty},
    ), previous


def test_room_stability():
    first, second = h.session(group=1, faculty=1), h.session(group=1, faculty=2)
    decoy, previous = _stability(
        {
            first.id: PreviousPlacement(MON, 1, room_id=1),
            second.id: PreviousPlacement(MON, 2, room_id=2),
        },
        room_change_penalty=1,
    )
    problem = h.problem([first, second], rooms=[h.room(1), h.room(2)], previous_placements=previous)
    off, on = _compare("room_stability", problem, [decoy], _soft("room_stability"))
    assert (off, on) == (1, 0)


def test_subject_day_spacing():
    problem = h.problem(h.sessions_of(2, group=1, faculty=1), days=(MON, TUE, WED))
    decoys = [h.avoid(1, 2, 3, 4, days=["WEDNESDAY"]), _soft("subject_spreading", weight=5)]
    off, on = _compare("subject_day_spacing", problem, decoys, _soft("subject_day_spacing"))
    assert (off, on) == (1, 0)


def test_group_daily_load_balance():
    problem = h.problem(
        [h.session(group=1, faculty=1), h.session(group=1, faculty=2)], days=(MON, TUE)
    )
    decoy = h.avoid(1, 2, 3, 4, days=["TUESDAY"])
    off, on = _compare(
        "group_daily_load_balance", problem, [decoy], _soft("group_daily_load_balance")
    )
    assert (off, on) == (2, 0)


def test_parallel_batch_labs():
    lab_type = h.SubjectType.LAB
    problem = h.problem(
        [
            h.session(group=2, faculty=1, subject_type=lab_type),
            h.session(group=3, faculty=2, subject_type=lab_type),
        ],
        rooms=[h.room(1), h.room(2)],
        academic_group_parent_ids={1: None, 2: 1, 3: 1},
        faculty_time_preferences={1: "MORNING", 2: "AFTERNOON"},
    )
    decoy = (
        "soft",
        "faculty_time_preference",
        {
            "enabled": True,
            "weight": 1,
            "ranges": {"MORNING": [1], "AFTERNOON": [4], "EVENING": [4]},
        },
    )
    off, on = _compare("parallel_batch_labs", problem, [decoy], _soft("parallel_batch_labs"))
    assert (off, on) == (2, 0)


def test_sibling_batches_may_share_a_slot_but_not_with_parent():
    lab_type = h.SubjectType.LAB
    sessions = [
        h.session(group=2, faculty=1, subject_type=lab_type),
        h.session(group=3, faculty=2, subject_type=lab_type),
        h.session(group=1, faculty=3),
    ]
    problem = h.problem(
        sessions,
        periods=2,
        rooms=[h.room(1), h.room(2)],
        academic_group_parent_ids={1: None, 2: 1, 3: 1},
    )
    result = solve(problem, h.config_with())
    by_group = {p.session.academic_group_id: p.start_period for p in result.timetable.placements}
    # Two periods only: the batches must run in parallel, the parent separately.
    assert by_group[2] == by_group[3] != by_group[1]


def test_room_size_fit():
    only = h.session(group=1, faculty=1)
    decoy, previous = _stability(
        {only.id: PreviousPlacement(MON, 1, room_id=1)}, room_change_penalty=1
    )
    problem = h.problem(
        [only],
        rooms=[h.room(1, capacity=100), h.room(2, capacity=40)],
        academic_group_capacities={1: 40},
        previous_placements=previous,
    )
    off, on = _compare("room_size_fit", problem, [decoy], _soft("room_size_fit", waste_unit=10))
    assert (off, on) == (6, 0)


def test_faculty_compact_days():
    problem = h.problem(h.sessions_of(2, group=1, faculty=1), days=(MON, TUE))
    decoys = [_soft("subject_spreading", weight=1)]
    off, on = _compare("faculty_compact_days", problem, decoys, _soft("faculty_compact_days"))
    assert (off, on) == (2, 1)


def test_consistent_subject_time():
    first, second = h.sessions_of(2, group=1, faculty=1)
    decoy, previous = _stability(
        {first.id: PreviousPlacement(MON, 1), second.id: PreviousPlacement(TUE, 2)}
    )
    problem = h.problem([first, second], days=(MON, TUE), previous_placements=previous)
    off, on = _compare(
        "consistent_subject_time",
        problem,
        [decoy, _soft("subject_spreading", weight=20)],
        _soft("consistent_subject_time"),
    )
    assert (off, on) == (1, 0)


def test_faculty_daily_load():
    problem = h.problem(
        [h.session(group=1, faculty=1), h.session(group=2, faculty=1)], days=(MON, TUE)
    )
    decoy = h.avoid(1, 2, 3, 4, days=["TUESDAY"])
    off, on = _compare(
        "faculty_daily_load", problem, [decoy], _soft("faculty_daily_load", max_periods=1)
    )
    assert (off, on) == (1, 0)


def test_online_at_day_edges():
    first = h.session(group=1, faculty=1)
    second = h.session(group=1, faculty=2)
    online = h.session(group=1, faculty=3, mode="ONLINE")
    decoy, previous = _stability(
        {
            first.id: PreviousPlacement(MON, 1, room_id=1),
            online.id: PreviousPlacement(MON, 2),
            second.id: PreviousPlacement(MON, 3, room_id=1),
        }
    )
    problem = h.problem([first, second, online], periods=4, previous_placements=previous)
    off, on = _compare("online_at_day_edges", problem, [decoy], _soft("online_at_day_edges"))
    assert (off, on) == (1, 0)


def test_faculty_preferred_day_off():
    problem = h.problem(
        [h.session(faculty=1, duration=2)],
        days=(MON, TUE),
        faculty_preferred_day_off={1: TUE},
    )
    decoy = h.avoid(1, 2, 3, 4, days=["MONDAY"])
    off, on = _compare(
        "faculty_preferred_day_off", problem, [decoy], _soft("faculty_preferred_day_off")
    )
    assert (off, on) == (2, 0)


def test_stability_vs_previous():
    only = h.session(faculty=1)
    problem = h.problem(
        [only], days=(MON, TUE), previous_placements={only.id: PreviousPlacement(TUE, 2)}
    )
    decoy = h.avoid(1, 2, 3, 4, days=["TUESDAY"])
    off, on = _compare("stability_vs_previous", problem, [decoy], _soft("stability_vs_previous"))
    assert (off, on) == (1, 0)


# ---------------------------------------------------------------------------
# Flexible constraints: off / soft / hard
# ---------------------------------------------------------------------------


def _lunch_problem(**session_kwargs):
    return h.problem(
        [h.session(faculty=1, duration=2, **session_kwargs)],
        periods=4,
        lunch_after_period=2,
    )


@pytest.mark.parametrize(
    ("mode", "allow", "expected_crossings"),
    [("off", False, 1), ("soft", False, 0), ("hard", False, 0), ("hard", True, 1)],
)
def test_no_session_across_lunch_modes(mode, allow, expected_crossings):
    problem = _lunch_problem(allow_across_lunch=allow)
    config = h.config_with(
        h.avoid(1, 4, weight=1),
        ("constraints", "no_session_across_lunch", {"mode": mode, "weight": 10}),
    )
    result = solve(problem, config)
    (placement,) = result.timetable.placements
    assert int(crosses_lunch(placement, 2)) == expected_crossings
    if mode == "soft":
        penalty = calculate_penalty(
            "no_session_across_lunch", result.timetable, problem.timetable_input, config
        )
        assert result.penalty("no_session_across_lunch") == penalty == expected_crossings


def test_hard_lunch_rule_reports_empty_domain():
    from app.domain.diagnostics import PreSolveError
    from app.domain.scheduling_candidate_domains import EmptyDomainsError

    problem = h.problem([h.session(duration=2)], periods=2, lunch_after_period=1)
    config = h.config_with(("constraints", "no_session_across_lunch", {"mode": "hard"}))

    with pytest.raises((EmptyDomainsError, PreSolveError)) as info:
        solve(problem, config)

    assert "crosses lunch" in str(info.value)


@pytest.mark.parametrize(
    ("key", "same"),
    [("faculty_max_consecutive", "faculty"), ("student_max_consecutive", "group")],
)
@pytest.mark.parametrize(("mode", "expected"), [("off", 1), ("soft", 0), ("hard", 0)])
def test_max_consecutive_modes(key, same, mode, expected):
    if same == "faculty":
        sessions = [h.session(group=index, faculty=1) for index in range(1, 4)]
    else:
        sessions = [h.session(group=1, faculty=index) for index in range(1, 4)]
    problem = h.problem(sessions, periods=4, rooms=[h.room(1), h.room(2), h.room(3)])
    config = h.config_with(
        h.avoid(4, weight=1),
        ("constraints", key, {"mode": mode, "weight": 10, "max_periods": 2}),
    )
    result = solve(problem, config)
    excess = calculate_penalty(key, result.timetable, problem.timetable_input, config)
    assert excess == expected
    if mode == "soft":
        assert result.penalty(key) == excess


def test_max_consecutive_windows_do_not_cross_lunch():
    sessions = [h.session(group=1, faculty=index) for index in range(1, 5)]
    problem = h.problem(
        sessions, periods=4, rooms=[h.room(i) for i in range(1, 5)], lunch_after_period=2
    )
    config = h.config_with(
        ("constraints", "student_max_consecutive", {"mode": "hard", "max_periods": 2}),
    )
    # P1-P4 are all busy, but lunch splits them into two runs of two.
    result = solve(problem, config)
    assert len(result.timetable.placements) == 4
