"""Pre-solve diagnostics.

These checks run before the CP-SAT model is built. They explain, in plain
language, why a problem cannot be solved (empty candidate domains, demand
exceeding capacity, conflicting locks, ...), so the user knows what to fix
or which optional constraint to relax.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from app.core.timetable_config import ConstraintMode, TimetableConfig
from app.domain.placement import SessionPlacement
from app.domain.populations import GroupHierarchy
from app.domain.room_suitability import is_room_suitable
from app.domain.time_slots import valid_start_periods
from app.domain.timetable import SchedulingSession, TimetableInput

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Diagnostic:
    severity: Severity
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.code}: {self.message}"


class PreSolveError(ValueError):
    """Raised when pre-solve checks prove the problem infeasible."""

    def __init__(self, diagnostics: list[Diagnostic]) -> None:
        self.diagnostics = diagnostics
        lines = "\n".join(f"  {item}" for item in diagnostics)
        super().__init__(f"Timetable problem is infeasible before solving:\n{lines}")


def _occupies(placement: SessionPlacement, day, period: int) -> bool:
    return placement.day == day and placement.start_period <= period <= placement.end_period


# ---------------------------------------------------------------------------
# Per-session explanations
# ---------------------------------------------------------------------------


def explain_no_placement(
    session: SchedulingSession,
    timetable_input: TimetableInput,
    config: TimetableConfig,
    hierarchy: GroupHierarchy,
) -> str:
    """Explain which rule removed the last valid placement of a session."""

    from app.domain.candidates import crosses_lunch

    periods_per_day = timetable_input.periods_per_day
    starts = valid_start_periods(
        periods_per_day=periods_per_day,
        duration_periods=session.duration_periods,
    )

    if not starts:
        return (
            f"duration {session.duration_periods} periods is longer than the "
            f"{periods_per_day}-period day"
        )

    placements = [
        SessionPlacement(session=session, day=day, start_period=start)
        for day in timetable_input.days
        for start in starts
    ]

    steps: list[tuple[str, object]] = []

    def blocked(placement: SessionPlacement) -> bool:
        return any(
            _occupies(placement, slot.day, slot.period) for slot in timetable_input.blocked_slots
        )

    steps.append(("every placement hits a global blocked slot", blocked))

    if config.hard.group_blocked_slots.enabled:
        blocks = [
            block
            for block in timetable_input.group_blocked_slots
            if hierarchy.populations_overlap(block.academic_group_id, session.academic_group_id)
        ]

        def group_blocked(placement: SessionPlacement) -> bool:
            return any(_occupies(placement, block.day, block.period) for block in blocks)

        steps.append(("every remaining placement hits a group blocked slot", group_blocked))

    if (
        config.constraints.no_session_across_lunch.mode == ConstraintMode.HARD
        and not session.allow_across_lunch
    ):
        steps.append(
            (
                "every remaining placement crosses lunch (no_session_across_lunch is hard; "
                "set allow_across_lunch on the assignment or use soft mode)",
                lambda placement: crosses_lunch(placement, timetable_input.lunch_after_period),
            )
        )

    if config.hard.locked_sessions.enabled:
        lock = next(
            (lock for lock in timetable_input.session_locks if lock.session_id == session.id),
            None,
        )

        if lock is not None:
            steps.append(
                (
                    f"the session is locked to {lock.day.value} P{lock.start_period}, "
                    "which is not a valid placement",
                    lambda placement: (
                        not (
                            placement.day == lock.day
                            and placement.start_period == lock.start_period
                        )
                    ),
                )
            )

    availability = (timetable_input.faculty_availability or {}).get(session.faculty_id)

    if availability is not None:
        steps.append(
            (
                f"faculty {session.faculty_id} is unavailable for every remaining placement",
                lambda placement: (
                    not availability.is_available(
                        day=placement.day,
                        start_period=placement.start_period,
                        duration_periods=session.duration_periods,
                    )
                ),
            )
        )

    for reason, rejects in steps:
        remaining = [placement for placement in placements if not rejects(placement)]

        if not remaining:
            return reason

        placements = remaining

    return "no valid placement (unknown reason)"


def explain_no_room(
    session: SchedulingSession,
    timetable_input: TimetableInput,
) -> str:
    """Explain why no room can host a session at any of its placements."""

    rooms = timetable_input.rooms or ()

    if not rooms:
        return "no rooms are configured"

    if session.required_room_type is not None:
        typed = [room for room in rooms if room.room_type.value == session.required_room_type]

        if not typed:
            return f"no room of the required type {session.required_room_type}"
    else:
        typed = list(rooms)

    capacities = timetable_input.academic_group_capacities

    if capacities is not None:
        group_size = capacities.get(session.academic_group_id)

        if group_size is None:
            return f"academic group {session.academic_group_id} has no capacity set"

        if all(room.capacity < group_size for room in typed):
            largest = max(room.capacity for room in typed)
            return (
                f"all {session.required_room_type or ''} rooms are too small: largest is "
                f"{largest}, group {session.academic_group_id} needs {group_size}"
            ).replace("all  rooms", "all rooms")

    suitable = [room for room in typed if is_room_suitable(session, room, timetable_input)]

    if suitable:
        return "every suitable room is unavailable (room unavailability or lock) at every placement"

    return "no suitable room"


# ---------------------------------------------------------------------------
# Aggregate checks
# ---------------------------------------------------------------------------


def _faculty_hours(timetable_input: TimetableInput) -> dict[int, int]:
    hours: dict[int, int] = defaultdict(int)
    for session in timetable_input.sessions:
        hours[session.faculty_id] += session.duration_periods
    return hours


def check_faculty_hours(
    timetable_input: TimetableInput,
    config: TimetableConfig,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    designations = timetable_input.faculty_designations or {}
    hours = _faculty_hours(timetable_input)

    if config.hard.faculty_weekly_cap.enabled:
        for faculty_id, total in sorted(hours.items()):
            designation = designations.get(faculty_id)
            if designation is None:
                continue
            cap = config.hard.faculty_weekly_cap.hours.for_designation(designation)
            if cap is not None and total > cap:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        "FACULTY_OVER_CAP",
                        f"faculty {faculty_id} ({designation}) is assigned {total} h/week, "
                        f"weekly cap is {cap}",
                    )
                )

    if config.hard.faculty_weekly_minimum.enabled:
        for faculty_id, designation in sorted(designations.items()):
            minimum = config.hard.faculty_weekly_minimum.hours.for_designation(designation)
            total = hours.get(faculty_id, 0)
            if minimum is not None and total < minimum:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        "FACULTY_UNDER_MINIMUM",
                        f"faculty {faculty_id} ({designation}) is assigned only {total} h/week, "
                        f"weekly minimum is {minimum}",
                    )
                )

    return diagnostics


def check_group_demand(
    timetable_input: TimetableInput,
    config: TimetableConfig,
    hierarchy: GroupHierarchy,
) -> list[Diagnostic]:
    """Each leaf population needs enough free slots for its own and its ancestors' sessions."""

    demand: dict[int, int] = defaultdict(int)

    for session in timetable_input.sessions:
        for leaf in hierarchy.leaves_of(session.academic_group_id):
            demand[leaf] += session.duration_periods

    total_slots = len(timetable_input.days) * timetable_input.periods_per_day
    global_blocked = {
        (slot.day, slot.period)
        for slot in timetable_input.blocked_slots
        if slot.day in timetable_input.days and slot.period <= timetable_input.periods_per_day
    }

    diagnostics: list[Diagnostic] = []

    for leaf, periods in sorted(demand.items()):
        blocked = set(global_blocked)

        if config.hard.group_blocked_slots.enabled:
            blocked.update(
                (block.day, block.period)
                for block in timetable_input.group_blocked_slots
                if block.academic_group_id in hierarchy.ancestors_or_self(leaf)
            )

        available = total_slots - len(blocked)

        if periods > available:
            diagnostics.append(
                Diagnostic(
                    "error",
                    "GROUP_OVER_CAPACITY",
                    f"academic group {leaf} needs {periods} periods/week (including parent "
                    f"groups) but only {available} slots are available",
                )
            )

    return diagnostics


def check_room_type_demand(timetable_input: TimetableInput) -> list[Diagnostic]:
    """In-person demand per room type must not exceed room-type supply."""

    rooms = timetable_input.rooms or ()
    supply: dict[str, int] = defaultdict(int)
    slots = len(timetable_input.days) * timetable_input.periods_per_day - len(
        timetable_input.blocked_slots
    )

    for room in rooms:
        supply[room.room_type.value] += slots

    demand: dict[str, int] = defaultdict(int)

    for session in timetable_input.sessions:
        if session.mode != "IN_PERSON" or session.required_room_type is None:
            continue
        demand[session.required_room_type] += session.duration_periods

    return [
        Diagnostic(
            "error",
            "ROOM_TYPE_OVER_CAPACITY",
            f"in-person sessions need {periods} {room_type} room-periods/week, "
            f"only {supply.get(room_type, 0)} are available",
        )
        for room_type, periods in sorted(demand.items())
        if periods > supply.get(room_type, 0)
    ]


def check_locks(
    timetable_input: TimetableInput,
    config: TimetableConfig,
    hierarchy: GroupHierarchy,
) -> list[Diagnostic]:
    """Report locks that reference unknown sessions or collide with each other."""

    if not config.hard.locked_sessions.enabled or not timetable_input.session_locks:
        return []

    sessions = {session.id: session for session in timetable_input.sessions}
    diagnostics: list[Diagnostic] = []
    locked: list[tuple[SessionPlacement, int | None]] = []
    seen: set[str] = set()

    for lock in timetable_input.session_locks:
        if lock.session_id in seen:
            diagnostics.append(
                Diagnostic("error", "LOCK_DUPLICATE", f"session {lock.session_id} is locked twice")
            )
            continue
        seen.add(lock.session_id)

        session = sessions.get(lock.session_id)

        if session is None:
            diagnostics.append(
                Diagnostic(
                    "warning",
                    "LOCK_UNKNOWN_SESSION",
                    f"lock refers to unknown or inactive session {lock.session_id}",
                )
            )
            continue

        locked.append(
            (
                SessionPlacement(session=session, day=lock.day, start_period=lock.start_period),
                lock.room_id,
            )
        )

    for index, (first, first_room) in enumerate(locked):
        for second, second_room in locked[index + 1 :]:
            if first.day != second.day or not (
                first.start_period <= second.end_period and second.start_period <= first.end_period
            ):
                continue

            reasons = []
            if first.session.faculty_id == second.session.faculty_id:
                reasons.append("same faculty")
            if hierarchy.populations_overlap(
                first.session.academic_group_id, second.session.academic_group_id
            ):
                reasons.append("shared students")
            if first_room is not None and first_room == second_room:
                reasons.append("same room")

            if reasons:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        "LOCK_CONFLICT",
                        f"locked sessions {first.session.id} and {second.session.id} overlap on "
                        f"{first.day.value} ({', '.join(reasons)})",
                    )
                )

    return diagnostics


def check_role_restrictions(
    timetable_input: TimetableInput,
    config: TimetableConfig,
) -> list[Diagnostic]:
    if not config.hard.role_restrictions.enabled:
        return []

    designations = timetable_input.faculty_designations or {}
    diagnostics: list[Diagnostic] = []
    reported: set[int] = set()

    for session in timetable_input.sessions:
        if session.teaching_assignment_id in reported:
            continue

        designation = designations.get(session.faculty_id)
        allowed = config.hard.role_restrictions.allowed_types(designation) if designation else None

        if allowed is None or session.subject_type is None:
            continue

        if session.subject_type.value not in allowed:
            reported.add(session.teaching_assignment_id)
            diagnostics.append(
                Diagnostic(
                    "error",
                    "ROLE_RESTRICTION",
                    f"assignment {session.teaching_assignment_id}: {designation} faculty "
                    f"{session.faculty_id} may only teach {sorted(allowed)}, "
                    f"not {session.subject_type.value}",
                )
            )

    return diagnostics


def run_presolve_checks(
    timetable_input: TimetableInput,
    config: TimetableConfig,
    hierarchy: GroupHierarchy | None = None,
) -> list[Diagnostic]:
    """Run all aggregate pre-solve checks (domains are checked separately)."""

    if hierarchy is None:
        hierarchy = GroupHierarchy(
            timetable_input.academic_group_parent_ids,
            (session.academic_group_id for session in timetable_input.sessions),
        )

    return [
        *check_faculty_hours(timetable_input, config),
        *check_group_demand(timetable_input, config, hierarchy),
        *check_room_type_demand(timetable_input),
        *check_locks(timetable_input, config, hierarchy),
        *check_role_restrictions(timetable_input, config),
    ]
