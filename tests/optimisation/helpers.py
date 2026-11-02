"""Builders for tiny solver instances used by the constraint tests."""

from __future__ import annotations

from app.core.timetable_config import TimetableConfig  # noqa: F401 - re-exported for tests
from app.db.models.subject import SubjectType
from app.domain.calendar import Day
from app.domain.problem import SchedulingProblem
from app.domain.room import RoomType, SchedulingRoom
from app.domain.timetable import SchedulingSession, TimetableInput

_counter = {"assignment": 1000}


def session(
    *,
    group: int = 1,
    faculty: int = 1,
    subject: int | None = None,
    duration: int = 1,
    mode: str = "IN_PERSON",
    room_type: str | None = "CLASSROOM",
    subject_type: SubjectType | None = SubjectType.LECTURE,
    number: int = 1,
    assignment: int | None = None,
    allow_across_lunch: bool = False,
) -> SchedulingSession:
    if assignment is None:
        _counter["assignment"] += 1
        assignment = _counter["assignment"]
    return SchedulingSession(
        id=f"assignment:{assignment}:session:{number}",
        teaching_assignment_id=assignment,
        subject_id=subject if subject is not None else assignment,
        course_id=1,
        academic_group_id=group,
        faculty_id=faculty,
        duration_periods=duration,
        mode=mode,
        required_room_type=room_type if mode != "ONLINE" else None,
        session_number=number,
        subject_type=subject_type,
        allow_across_lunch=allow_across_lunch,
    )


def sessions_of(count: int, **kwargs) -> list[SchedulingSession]:
    _counter["assignment"] += 1
    assignment = _counter["assignment"]
    return [session(number=index, assignment=assignment, **kwargs) for index in range(1, count + 1)]


def room(room_id: int = 1, capacity: int = 100, room_type: RoomType = RoomType.CLASSROOM):
    return SchedulingRoom(id=room_id, room_type=room_type, capacity=capacity)


def problem(
    sessions,
    *,
    days=(Day.MONDAY,),
    periods: int = 4,
    rooms=None,
    **kwargs,
) -> SchedulingProblem:
    return SchedulingProblem(
        timetable_input=TimetableInput(
            days=tuple(days),
            periods_per_day=periods,
            sessions=tuple(sessions),
            rooms=tuple(rooms) if rooms is not None else (room(),),
            **kwargs,
        )
    )


def base_config(**solver) -> dict:
    """Config dict with every optional constraint off (hard span/cap off too)."""

    config = TimetableConfig()
    data = config.model_dump(mode="json")

    for key in data["soft"]:
        data["soft"][key]["enabled"] = False
    for key in data["constraints"]:
        data["constraints"][key]["mode"] = "off"
    for key in data["hard"]:
        data["hard"][key]["enabled"] = False

    data["solver"].update({"max_time_seconds": 10, "workers": 4, "random_seed": 1, **solver})
    return data


def config_with(*items: tuple[str, str, dict], base: dict | None = None) -> TimetableConfig:
    """Build a config from ``base_config`` plus ``(section, key, values)`` overrides."""

    data = base or base_config()
    for section, key, values in items:
        data[section][key].update(values)
    return TimetableConfig.model_validate(data)


def avoid(*periods: int, penalty: int = 1, weight: int = 1, days=None, subject_types=None):
    """An ``avoid_periods`` override used as a 'decoy' preference."""

    rules = [
        {
            "period": period,
            "penalty": penalty,
            **({"days": list(days)} if days else {}),
            **({"subject_types": list(subject_types)} if subject_types else {}),
        }
        for period in periods
    ]
    return ("soft", "avoid_periods", {"enabled": True, "weight": weight, "rules": rules})
