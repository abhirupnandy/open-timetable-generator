"""Independent hard-constraint validator.

Checks a finished timetable against every hard rule without using solver
variables, so it can catch modelling bugs in the CP-SAT formulation.

* ``conflicts``: pairs of overlapping sessions sharing a faculty member,
  students (via the group hierarchy) or a room.
* ``violations``: single-session or aggregate rule failures (grid, rooms,
  blocked slots, locks, workload, span, optional hard constraints).
  These are only checked when ``timetable_input`` is supplied.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import StrEnum

from app.core.timetable_config import ConstraintMode, TimetableConfig
from app.domain.calendar import DEFAULT_PERIOD_TIMES
from app.domain.candidates import crosses_lunch
from app.domain.hard_constraints import (
    HardConflictReason,
    hard_conflict_reasons,
)
from app.domain.placement import SessionPlacement, placements_overlap
from app.domain.populations import GroupHierarchy
from app.domain.schedule import Timetable
from app.domain.timetable import TimetableInput


class HardViolationReason(StrEnum):
    MISSING_SESSION = "MISSING_SESSION"
    DUPLICATE_SESSION = "DUPLICATE_SESSION"
    UNKNOWN_SESSION = "UNKNOWN_SESSION"
    OUTSIDE_GRID = "OUTSIDE_GRID"
    ROOM_TYPE = "ROOM_TYPE"
    ROOM_CAPACITY = "ROOM_CAPACITY"
    ONLINE_WITH_ROOM = "ONLINE_WITH_ROOM"
    IN_PERSON_WITHOUT_ROOM = "IN_PERSON_WITHOUT_ROOM"
    ROOM_UNAVAILABLE = "ROOM_UNAVAILABLE"
    FACULTY_UNAVAILABLE = "FACULTY_UNAVAILABLE"
    BLOCKED_SLOT = "BLOCKED_SLOT"
    GROUP_BLOCKED_SLOT = "GROUP_BLOCKED_SLOT"
    LOCK_VIOLATED = "LOCK_VIOLATED"
    WEEKLY_CAP = "WEEKLY_CAP"
    WEEKLY_MINIMUM = "WEEKLY_MINIMUM"
    DAILY_SPAN = "DAILY_SPAN"
    ACROSS_LUNCH = "ACROSS_LUNCH"
    FACULTY_MAX_CONSECUTIVE = "FACULTY_MAX_CONSECUTIVE"
    STUDENT_MAX_CONSECUTIVE = "STUDENT_MAX_CONSECUTIVE"
    ROLE_RESTRICTION = "ROLE_RESTRICTION"


@dataclass(frozen=True)
class HardConflict:
    """A pair of sessions that violate one or more hard constraints."""

    first_session_id: str
    second_session_id: str
    reasons: tuple[HardConflictReason, ...]


@dataclass(frozen=True)
class HardViolation:
    """A single hard-rule failure that is not a pairwise overlap."""

    reason: HardViolationReason
    message: str
    session_id: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a candidate timetable."""

    conflicts: tuple[HardConflict, ...]
    violations: tuple[HardViolation, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.conflicts and not self.violations

    def violations_of(self, reason: HardViolationReason) -> tuple[HardViolation, ...]:
        return tuple(item for item in self.violations if item.reason == reason)


def _pairwise_conflicts(
    timetable: Timetable,
    academic_group_parent_ids: dict[int, int | None] | None,
) -> list[HardConflict]:
    rooms = {
        assignment.placement.session.id: assignment.room.id
        for assignment in timetable.room_assignments
    }

    by_day: dict[object, list[SessionPlacement]] = defaultdict(list)
    for placement in timetable.placements:
        by_day[placement.day].append(placement)

    conflicts: list[HardConflict] = []
    order = {placement.session.id: index for index, placement in enumerate(timetable.placements)}

    for placements in by_day.values():
        for index, first in enumerate(placements):
            for second in placements[index + 1 :]:
                reasons = list(hard_conflict_reasons(first, second, academic_group_parent_ids))

                first_room = rooms.get(first.session.id)
                if (
                    first_room is not None
                    and first_room == rooms.get(second.session.id)
                    and placements_overlap(first, second)
                ):
                    reasons.append(HardConflictReason.ROOM)

                if reasons:
                    conflicts.append(
                        HardConflict(
                            first_session_id=first.session.id,
                            second_session_id=second.session.id,
                            reasons=tuple(reasons),
                        )
                    )

    conflicts.sort(key=lambda item: (order[item.first_session_id], order[item.second_session_id]))
    return conflicts


def _occupies(placement: SessionPlacement, day, period: int) -> bool:
    return placement.day == day and placement.start_period <= period <= placement.end_period


def _rule_violations(
    timetable: Timetable,
    timetable_input: TimetableInput,
    config: TimetableConfig,
) -> list[HardViolation]:
    violations: list[HardViolation] = []

    def add(reason: HardViolationReason, message: str, session_id: str | None = None) -> None:
        violations.append(HardViolation(reason, message, session_id))

    hierarchy = GroupHierarchy(
        timetable_input.academic_group_parent_ids,
        (session.academic_group_id for session in timetable_input.sessions),
    )
    rooms = {
        assignment.placement.session.id: assignment.room
        for assignment in timetable.room_assignments
    }

    # -- completeness ------------------------------------------------------
    expected = {session.id for session in timetable_input.sessions}
    counts = Counter(placement.session.id for placement in timetable.placements)

    for session_id in sorted(expected - counts.keys()):
        add(HardViolationReason.MISSING_SESSION, f"{session_id} is not placed", session_id)
    for session_id, count in sorted(counts.items()):
        if count > 1:
            add(
                HardViolationReason.DUPLICATE_SESSION,
                f"{session_id} placed {count} times",
                session_id,
            )
        if session_id not in expected:
            add(
                HardViolationReason.UNKNOWN_SESSION, f"{session_id} is not in the input", session_id
            )

    capacities = timetable_input.academic_group_capacities
    lunch_hard = config.constraints.no_session_across_lunch.mode == ConstraintMode.HARD
    locks = (
        {lock.session_id: lock for lock in timetable_input.session_locks}
        if config.hard.locked_sessions.enabled
        else {}
    )
    designations = timetable_input.faculty_designations or {}

    # -- per placement -----------------------------------------------------
    for placement in timetable.placements:
        session = placement.session
        sid = session.id
        room = rooms.get(sid)

        if (
            placement.day not in timetable_input.days
            or placement.start_period < 1
            or placement.end_period > timetable_input.periods_per_day
        ):
            add(HardViolationReason.OUTSIDE_GRID, f"{sid} does not fit the timetable grid", sid)

        if session.mode == "ONLINE" and room is not None:
            add(
                HardViolationReason.ONLINE_WITH_ROOM,
                f"online session {sid} has room {room.id}",
                sid,
            )
        if session.mode == "IN_PERSON" and room is None:
            add(
                HardViolationReason.IN_PERSON_WITHOUT_ROOM,
                f"in-person session {sid} has no room",
                sid,
            )

        if room is not None:
            if (
                session.required_room_type is not None
                and room.room_type.value != session.required_room_type
            ):
                add(
                    HardViolationReason.ROOM_TYPE,
                    f"{sid} needs {session.required_room_type}, got {room.room_type.value}",
                    sid,
                )
            if capacities is not None:
                size = capacities.get(session.academic_group_id)
                if size is None or room.capacity < size:
                    add(
                        HardViolationReason.ROOM_CAPACITY,
                        f"{sid}: room {room.id} capacity {room.capacity} < group size {size}",
                        sid,
                    )
            availability = (timetable_input.room_availability or {}).get(room.id)
            if availability is not None and not availability.is_available(
                day=placement.day,
                start_period=placement.start_period,
                duration_periods=session.duration_periods,
            ):
                add(HardViolationReason.ROOM_UNAVAILABLE, f"{sid}: room {room.id} unavailable", sid)

        availability = (timetable_input.faculty_availability or {}).get(session.faculty_id)
        if availability is not None and not availability.is_available(
            day=placement.day,
            start_period=placement.start_period,
            duration_periods=session.duration_periods,
        ):
            add(
                HardViolationReason.FACULTY_UNAVAILABLE,
                f"{sid}: faculty {session.faculty_id} unavailable",
                sid,
            )

        for slot in timetable_input.blocked_slots:
            if _occupies(placement, slot.day, slot.period):
                add(
                    HardViolationReason.BLOCKED_SLOT,
                    f"{sid} uses blocked slot {slot.day.value} P{slot.period}",
                    sid,
                )

        if config.hard.group_blocked_slots.enabled:
            for block in timetable_input.group_blocked_slots:
                if _occupies(placement, block.day, block.period) and hierarchy.populations_overlap(
                    block.academic_group_id, session.academic_group_id
                ):
                    add(
                        HardViolationReason.GROUP_BLOCKED_SLOT,
                        f"{sid} uses {block.day.value} P{block.period}, blocked for group "
                        f"{block.academic_group_id}",
                        sid,
                    )

        lock = locks.get(sid)
        if lock is not None and (
            placement.day != lock.day
            or placement.start_period != lock.start_period
            or (lock.room_id is not None and (room is None or room.id != lock.room_id))
        ):
            add(HardViolationReason.LOCK_VIOLATED, f"{sid} does not match its lock", sid)

        if (
            lunch_hard
            and not session.allow_across_lunch
            and crosses_lunch(placement, timetable_input.lunch_after_period)
        ):
            add(HardViolationReason.ACROSS_LUNCH, f"{sid} spans lunch", sid)

        if config.hard.role_restrictions.enabled and session.subject_type is not None:
            designation = designations.get(session.faculty_id)
            allowed = (
                config.hard.role_restrictions.allowed_types(designation) if designation else None
            )
            if allowed is not None and session.subject_type.value not in allowed:
                add(
                    HardViolationReason.ROLE_RESTRICTION,
                    f"{sid}: {designation} may not teach {session.subject_type.value}",
                    sid,
                )

    # -- aggregates --------------------------------------------------------
    hours: dict[int, int] = defaultdict(int)
    for placement in timetable.placements:
        hours[placement.session.faculty_id] += placement.session.duration_periods

    if config.hard.faculty_weekly_cap.enabled:
        for faculty_id, total in sorted(hours.items()):
            designation = designations.get(faculty_id)
            cap = (
                config.hard.faculty_weekly_cap.hours.for_designation(designation)
                if designation
                else None
            )
            if cap is not None and total > cap:
                add(HardViolationReason.WEEKLY_CAP, f"faculty {faculty_id}: {total} h > cap {cap}")

    if config.hard.faculty_weekly_minimum.enabled:
        for faculty_id, designation in sorted(designations.items()):
            minimum = config.hard.faculty_weekly_minimum.hours.for_designation(designation)
            if minimum is not None and hours.get(faculty_id, 0) < minimum:
                add(
                    HardViolationReason.WEEKLY_MINIMUM,
                    f"faculty {faculty_id}: {hours.get(faculty_id, 0)} h < minimum {minimum}",
                )

    faculty_days: dict[tuple[int, object], list[SessionPlacement]] = defaultdict(list)
    for placement in timetable.placements:
        faculty_days[(placement.session.faculty_id, placement.day)].append(placement)

    if config.hard.faculty_daily_span.enabled:
        times = timetable_input.period_times or DEFAULT_PERIOD_TIMES
        limit = config.hard.faculty_daily_span.max_minutes
        for (faculty_id, day), placements in sorted(
            faculty_days.items(), key=lambda item: (item[0][0], str(item[0][1]))
        ):
            if any(p.start_period not in times or p.end_period not in times for p in placements):
                continue  # outside the grid; reported as OUTSIDE_GRID
            start = min(times[p.start_period][0] for p in placements)
            end = max(times[p.end_period][1] for p in placements)
            if end - start > limit:
                add(
                    HardViolationReason.DAILY_SPAN,
                    f"faculty {faculty_id} on {day}: span {end - start} min > {limit}",
                )

    def half_days() -> list[tuple[int, ...]]:
        periods = tuple(range(1, timetable_input.periods_per_day + 1))
        lunch = timetable_input.lunch_after_period
        if lunch is None or not (1 <= lunch < len(periods)):
            return [periods]
        return [periods[:lunch], periods[lunch:]]

    def check_consecutive(occupancy, limit: int, reason: HardViolationReason, label: str) -> None:
        for (entity, day), periods in sorted(occupancy.items(), key=lambda item: str(item[0])):
            for block in half_days():
                run = 0
                for period in block:
                    run = run + 1 if period in periods else 0
                    if run > limit:
                        add(reason, f"{label} {entity} on {day}: more than {limit} consecutive")
                        break
                else:
                    continue
                break

    faculty_max = config.constraints.faculty_max_consecutive
    if faculty_max.mode == ConstraintMode.HARD:
        occupancy = {
            key: {period for p in placements for period in p.occupied_periods}
            for key, placements in faculty_days.items()
        }
        check_consecutive(
            occupancy,
            faculty_max.max_periods,
            HardViolationReason.FACULTY_MAX_CONSECUTIVE,
            "faculty",
        )

    student_max = config.constraints.student_max_consecutive
    if student_max.mode == ConstraintMode.HARD:
        occupancy: dict[tuple[int, object], set[int]] = defaultdict(set)
        for placement in timetable.placements:
            for leaf in hierarchy.leaves_of(placement.session.academic_group_id):
                occupancy[(leaf, placement.day)].update(placement.occupied_periods)
        check_consecutive(
            occupancy, student_max.max_periods, HardViolationReason.STUDENT_MAX_CONSECUTIVE, "group"
        )

    return violations


def validate_timetable(
    timetable: Timetable,
    academic_group_parent_ids: dict[int, int | None] | None = None,
    *,
    timetable_input: TimetableInput | None = None,
    config: TimetableConfig | None = None,
) -> ValidationResult:
    """Validate a candidate timetable.

    Pass ``timetable_input`` (and the ``config`` used to solve) to check
    every hard rule; without it only pairwise overlaps are checked.
    If ``academic_group_parent_ids`` is omitted it is taken from
    ``timetable_input``.
    """

    if academic_group_parent_ids is None and timetable_input is not None:
        academic_group_parent_ids = timetable_input.academic_group_parent_ids

    conflicts = _pairwise_conflicts(timetable, academic_group_parent_ids)

    violations: list[HardViolation] = []
    if timetable_input is not None:
        violations = _rule_violations(timetable, timetable_input, config or TimetableConfig())

    return ValidationResult(conflicts=tuple(conflicts), violations=tuple(violations))
