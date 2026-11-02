from __future__ import annotations

import pytest

from app.core.timetable_config import TimetableConfig
from app.db.models.subject import SubjectType
from app.domain.availability import AvailabilityWindow
from app.domain.calendar import Day
from app.domain.diagnostics import PreSolveError, run_presolve_checks
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import RoomType, SchedulingRoom
from app.domain.scheduling_candidate_domains import (
    EmptyDomainsError,
    build_scheduling_candidate_domains,
)
from app.domain.timetable import GroupBlockedSlot, SessionLock, TimeSlot
from app.optimisation.solver import InfeasibleTimetableError, solve
from tests.optimisation import helpers as h


def codes(diagnostics):
    return {item.code for item in diagnostics}


def _empty_reason(problem, config=None):
    with pytest.raises(EmptyDomainsError) as info:
        build_scheduling_candidate_domains(problem, config)
    return info.value.reason


def test_empty_domain_reasons():
    assert "longer than" in _empty_reason(h.problem([h.session(duration=5)], periods=4))
    assert "global blocked slot" in _empty_reason(
        h.problem([h.session(duration=1)], periods=1, blocked_slots=(TimeSlot(Day.MONDAY, 1),))
    )
    assert "group blocked slot" in _empty_reason(
        h.problem(
            [h.session(group=2)],
            periods=1,
            group_blocked_slots=(GroupBlockedSlot(1, Day.MONDAY, 1),),
            academic_group_parent_ids={1: None, 2: 1},
        )
    )
    assert "faculty 1 is unavailable" in _empty_reason(
        h.problem(
            [h.session(faculty=1, duration=2)],
            faculty_availability={
                1: ResourceAvailability(1, (AvailabilityWindow(Day.MONDAY, 1, 1),))
            },
        )
    )
    assert "no room of the required type COMPUTER_LAB" in _empty_reason(
        h.problem([h.session(room_type="COMPUTER_LAB")])
    )
    assert "too small" in _empty_reason(
        h.problem([h.session(group=1)], academic_group_capacities={1: 500})
    )
    assert "has no capacity set" in _empty_reason(
        h.problem([h.session(group=1)], academic_group_capacities={2: 10})
    )
    assert "locked to" in _empty_reason(
        h.problem(
            [h.session(assignment=1, number=1)],
            periods=2,
            session_locks=(SessionLock("assignment:1:session:1", Day.MONDAY, 3),),
        )
    )


def test_empty_domain_lists_every_session():
    problem = h.problem([h.session(duration=5), h.session(room_type="SPECIAL_LAB")])
    with pytest.raises(EmptyDomainsError) as info:
        build_scheduling_candidate_domains(problem)
    assert len(info.value.diagnostics) == 2


def test_capacity_checks():
    config = TimetableConfig()
    over_cap = h.problem(h.sessions_of(9, faculty=1), periods=8, days=(Day.MONDAY, Day.TUESDAY))
    designations = {1: "PHD_SCHOLAR"}
    problem = h.problem(
        h.sessions_of(9, faculty=1),
        periods=4,
        days=(Day.MONDAY,),
        faculty_designations=designations,
    )
    found = codes(run_presolve_checks(problem.timetable_input, config))
    assert {"FACULTY_OVER_CAP", "GROUP_OVER_CAPACITY", "ROOM_TYPE_OVER_CAPACITY"} <= found
    assert "FACULTY_OVER_CAP" not in codes(run_presolve_checks(over_cap.timetable_input, config))


def test_minimum_lock_and_role_checks():
    data = TimetableConfig().model_dump(mode="json")
    data["hard"]["faculty_weekly_minimum"]["enabled"] = True
    data["hard"]["role_restrictions"]["enabled"] = True
    config = TimetableConfig.model_validate(data)

    first = h.session(faculty=1, group=1, assignment=1)
    second = h.session(faculty=1, group=2, assignment=2)
    problem = h.problem(
        [first, second],
        faculty_designations={1: "PROFESSOR", 2: "PHD_SCHOLAR"},
        session_locks=(
            SessionLock(first.id, Day.MONDAY, 1),
            SessionLock(second.id, Day.MONDAY, 1),
        ),
    )
    found = run_presolve_checks(problem.timetable_input, config)
    assert {"FACULTY_UNDER_MINIMUM", "LOCK_CONFLICT"} <= codes(found)

    phd = h.problem(
        [h.session(faculty=2, subject_type=SubjectType.LECTURE)],
        faculty_designations={2: "PHD_SCHOLAR"},
    )
    assert "ROLE_RESTRICTION" in codes(run_presolve_checks(phd.timetable_input, config))


def test_solve_raises_presolve_error_with_reasons():
    problem = h.problem(
        h.sessions_of(14, faculty=1),
        periods=8,
        days=(Day.MONDAY, Day.TUESDAY),
        faculty_designations={1: "PHD_SCHOLAR"},
        rooms=[h.room(1), h.room(2)],
    )
    with pytest.raises(PreSolveError, match="weekly cap is 8"):
        solve(problem)


def test_infeasible_model_reports_enabled_hard_constraints():
    # Two 1-period sessions for one faculty in a 1-period day: no aggregate
    # check catches it, CP-SAT proves it infeasible.
    problem = h.problem(
        [h.session(faculty=1, group=1), h.session(faculty=1, group=2)],
        periods=1,
        rooms=[h.room(1), SchedulingRoom(2, RoomType.CLASSROOM, 100)],
    )
    with pytest.raises(InfeasibleTimetableError) as info:
        solve(problem)
    message = str(info.value)
    assert "INFEASIBLE" in message
    assert "faculty_daily_span" in message
