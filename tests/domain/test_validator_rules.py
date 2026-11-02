"""A deliberately broken timetable triggers each hard-rule failure type."""

from __future__ import annotations

import pytest

from app.core.timetable_config import TimetableConfig
from app.db.models.subject import SubjectType
from app.domain.availability import AvailabilityWindow
from app.domain.calendar import Day
from app.domain.hard_constraints import HardConflictReason
from app.domain.placement import SessionPlacement
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import RoomType, SchedulingRoom
from app.domain.room_assignment import RoomAssignment
from app.domain.schedule import Timetable
from app.domain.timetable import (
    GroupBlockedSlot,
    SchedulingSession,
    SessionLock,
    TimeSlot,
    TimetableInput,
)
from app.domain.validator import HardViolationReason as R
from app.domain.validator import validate_timetable

MON = Day.MONDAY
CLASSROOM = SchedulingRoom(1, RoomType.CLASSROOM, 50)
LAB = SchedulingRoom(2, RoomType.COMPUTER_LAB, 30)


def make(sid, *, group=1, faculty=1, duration=1, mode="IN_PERSON", room_type="CLASSROOM", **kw):
    return SchedulingSession(
        id=sid,
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=group,
        faculty_id=faculty,
        duration_periods=duration,
        mode=mode,
        required_room_type=room_type,
        session_number=1,
        **kw,
    )


def check(placements, rooms=None, config=None, **input_kwargs):
    sessions = tuple({p.session.id: p.session for p in placements}.values())
    timetable_input = TimetableInput(
        days=(MON, Day.TUESDAY),
        periods_per_day=input_kwargs.pop("periods", 8),
        sessions=input_kwargs.pop("sessions", sessions),
        rooms=(CLASSROOM, LAB),
        **input_kwargs,
    )
    timetable = Timetable(
        placements=tuple(placements),
        room_assignments=tuple(
            RoomAssignment(placement=placement, room=room)
            for placement, room in zip(placements, rooms or [], strict=False)
            if room is not None
        ),
    )
    return validate_timetable(timetable, timetable_input=timetable_input, config=config)


def config(**overrides):
    data = TimetableConfig().model_dump(mode="json")
    for dotted, value in overrides.items():
        section, key, field = dotted.split("__")
        data[section][key][field] = value
    return TimetableConfig.model_validate(data)


def at(session, start=1, day=MON):
    return SessionPlacement(session=session, day=day, start_period=start)


def reasons(result):
    return {violation.reason for violation in result.violations}


def test_valid_timetable_passes():
    result = check([at(make("a"))], rooms=[CLASSROOM])
    assert result.is_valid


def test_pairwise_room_and_population_conflicts_use_parent_map():
    parent = at(make("parent", group=1, faculty=1))
    batch = at(make("batch", group=2, faculty=2))
    sibling_a = at(make("b1", group=2, faculty=3), start=3)
    sibling_b = at(make("b2", group=3, faculty=4), start=3)
    result = check(
        [parent, batch, sibling_a, sibling_b],
        rooms=[CLASSROOM, LAB, None, None],
        academic_group_parent_ids={1: None, 2: 1, 3: 1},
    )
    pairs = {(c.first_session_id, c.second_session_id): c.reasons for c in result.conflicts}
    assert pairs == {("parent", "batch"): (HardConflictReason.ACADEMIC_GROUP,)}

    same_room = check(
        [at(make("x", group=1, faculty=1)), at(make("y", group=2, faculty=2))],
        rooms=[CLASSROOM, CLASSROOM],
    )
    assert same_room.conflicts[0].reasons == (HardConflictReason.ROOM,)


@pytest.mark.parametrize(
    ("placements", "rooms", "kwargs", "expected"),
    [
        ([at(make("a"), start=8)], [CLASSROOM], {"periods": 7}, R.OUTSIDE_GRID),
        ([at(make("a"))], [LAB], {}, R.ROOM_TYPE),
        ([at(make("a"))], [CLASSROOM], {"academic_group_capacities": {1: 80}}, R.ROOM_CAPACITY),
        ([at(make("a", mode="ONLINE", room_type=None))], [CLASSROOM], {}, R.ONLINE_WITH_ROOM),
        ([at(make("a"))], [], {}, R.IN_PERSON_WITHOUT_ROOM),
        (
            [at(make("a"), start=6)],
            [CLASSROOM],
            {"blocked_slots": (TimeSlot(MON, 6),)},
            R.BLOCKED_SLOT,
        ),
        (
            [at(make("a", group=2))],
            [CLASSROOM],
            {
                "group_blocked_slots": (GroupBlockedSlot(1, MON, 1),),
                "academic_group_parent_ids": {1: None, 2: 1},
            },
            R.GROUP_BLOCKED_SLOT,
        ),
        (
            [at(make("a"))],
            [CLASSROOM],
            {"session_locks": (SessionLock("a", Day.TUESDAY, 1),)},
            R.LOCK_VIOLATED,
        ),
        (
            [at(make("a"))],
            [CLASSROOM],
            {
                "faculty_availability": {
                    1: ResourceAvailability(1, (AvailabilityWindow(MON, 2, 8),))
                }
            },
            R.FACULTY_UNAVAILABLE,
        ),
        (
            [at(make("a"))],
            [CLASSROOM],
            {"room_availability": {1: ResourceAvailability(1, (AvailabilityWindow(MON, 3, 8),))}},
            R.ROOM_UNAVAILABLE,
        ),
        (
            [at(make("a")), at(make("b", group=2), start=8)],
            [CLASSROOM, CLASSROOM],
            {},
            R.DAILY_SPAN,
        ),
        (
            [at(make("a", duration=5)), at(make("b", duration=4, group=2), day=Day.TUESDAY)],
            [CLASSROOM, CLASSROOM],
            {"faculty_designations": {1: "PHD_SCHOLAR"}},
            R.WEEKLY_CAP,
        ),
        ([], [], {"sessions": (make("a"),)}, R.MISSING_SESSION),
        (
            [at(make("a")), at(make("a"), day=Day.TUESDAY)],
            [CLASSROOM, CLASSROOM],
            {},
            R.DUPLICATE_SESSION,
        ),
    ],
)
def test_each_default_rule_is_detected(placements, rooms, kwargs, expected):
    result = check(placements, rooms=rooms, **kwargs)
    assert expected in reasons(result)
    assert not result.is_valid


def test_optional_rules_only_apply_when_enabled():
    lunch = [at(make("a", duration=2), start=4)]
    assert R.ACROSS_LUNCH not in reasons(check(lunch, rooms=[CLASSROOM], lunch_after_period=4))
    hard = config(constraints__no_session_across_lunch__mode="hard")
    assert R.ACROSS_LUNCH in reasons(
        check(lunch, rooms=[CLASSROOM], lunch_after_period=4, config=hard)
    )
    exempt = [at(make("a", duration=2, allow_across_lunch=True), start=4)]
    assert R.ACROSS_LUNCH not in reasons(
        check(exempt, rooms=[CLASSROOM], lunch_after_period=4, config=hard)
    )

    minimum = config(hard__faculty_weekly_minimum__enabled=True)
    assert R.WEEKLY_MINIMUM in reasons(
        check(
            [at(make("a"))],
            rooms=[CLASSROOM],
            faculty_designations={1: "PROFESSOR"},
            config=minimum,
        )
    )

    roles = config(hard__role_restrictions__enabled=True)
    lecture = make("a", subject_type=SubjectType.LECTURE)
    assert R.ROLE_RESTRICTION in reasons(
        check(
            [at(lecture)], rooms=[CLASSROOM], faculty_designations={1: "PHD_SCHOLAR"}, config=roles
        )
    )


def test_hard_max_consecutive_rules():
    runs = [at(make(f"s{i}", group=i), start=i) for i in range(1, 5)]
    rooms = [CLASSROOM] * 4
    hard = config(
        constraints__faculty_max_consecutive__mode="hard",
        constraints__student_max_consecutive__mode="hard",
        constraints__student_max_consecutive__max_periods=3,
    )
    result = check(runs, rooms=[None] * 4, config=hard)
    assert R.FACULTY_MAX_CONSECUTIVE in reasons(result)

    group_runs = [at(make(f"g{i}", faculty=i), start=i) for i in range(1, 5)]
    assert R.STUDENT_MAX_CONSECUTIVE in reasons(check(group_runs, rooms=rooms, config=hard))
