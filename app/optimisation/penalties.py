"""Independent post-solve penalty calculators.

Pure Python, no solver variables. Each function recomputes one constraint's
raw penalty from a finished timetable so it can be compared with the value
the CP-SAT model reported (a mismatch indicates a modelling bug).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from app.core.timetable_config import ConstraintMode, TimetableConfig
from app.domain.calendar import Day
from app.domain.candidates import crosses_lunch
from app.domain.placement import SessionPlacement
from app.domain.populations import GroupHierarchy
from app.domain.room import SchedulingRoom
from app.domain.schedule import Timetable
from app.domain.timetable import TimetableInput
from app.optimisation.faculty_workload import FacultyWorkload, calculate_s2_penalty

_WEEKDAY_ORDER = {day: index for index, day in enumerate(Day)}


@dataclass
class TimetableFacts:
    """Indexes over a finished timetable shared by all calculators."""

    timetable: Timetable
    timetable_input: TimetableInput
    config: TimetableConfig
    hierarchy: GroupHierarchy
    rooms: dict[str, SchedulingRoom]

    @classmethod
    def build(
        cls,
        timetable: Timetable,
        timetable_input: TimetableInput,
        config: TimetableConfig,
    ) -> TimetableFacts:
        hierarchy = GroupHierarchy(
            timetable_input.academic_group_parent_ids,
            (session.academic_group_id for session in timetable_input.sessions),
        )
        rooms = {
            assignment.placement.session.id: assignment.room
            for assignment in timetable.room_assignments
        }
        return cls(timetable, timetable_input, config, hierarchy, rooms)

    @property
    def placements(self) -> tuple[SessionPlacement, ...]:
        return self.timetable.placements

    @property
    def periods_per_day(self) -> int:
        return self.timetable_input.periods_per_day

    def room_of(self, placement: SessionPlacement) -> SchedulingRoom | None:
        return self.rooms.get(placement.session.id)

    def leaf_occupancy(self, *, in_person_only: bool = False) -> dict[tuple[int, Day], set[int]]:
        occupied: dict[tuple[int, Day], set[int]] = defaultdict(set)
        for placement in self.placements:
            if in_person_only and self.room_of(placement) is None:
                continue
            for leaf in self.hierarchy.leaves_of(placement.session.academic_group_id):
                occupied[(leaf, placement.day)].update(placement.occupied_periods)
        return occupied

    def faculty_occupancy(self) -> dict[tuple[int, Day], set[int]]:
        occupied: dict[tuple[int, Day], set[int]] = defaultdict(set)
        for placement in self.placements:
            occupied[(placement.session.faculty_id, placement.day)].update(
                placement.occupied_periods
            )
        return occupied

    def half_days(self) -> list[tuple[int, ...]]:
        periods = tuple(range(1, self.periods_per_day + 1))
        lunch = self.timetable_input.lunch_after_period
        if lunch is None or not (1 <= lunch < len(periods)):
            return [periods]
        return [periods[:lunch], periods[lunch:]]


def _gaps(periods: set[int]) -> int:
    if len(periods) < 2:
        return 0
    return sum(1 for period in range(min(periods), max(periods) + 1) if period not in periods)


# ---------------------------------------------------------------------------
# Flexible
# ---------------------------------------------------------------------------


def lunch_crossings(facts: TimetableFacts, _config=None) -> int:
    lunch = facts.timetable_input.lunch_after_period
    return sum(
        1
        for placement in facts.placements
        if not placement.session.allow_across_lunch and crosses_lunch(placement, lunch)
    )


def _consecutive_excess(facts: TimetableFacts, occupancy, limit: int) -> int:
    size = limit + 1
    total = 0
    for periods in occupancy.values():
        for block in facts.half_days():
            for start in range(0, len(block) - size + 1):
                window = block[start : start + size]
                count = sum(1 for period in window if period in periods)
                total += max(0, count - limit)
    return total


def faculty_max_consecutive(facts: TimetableFacts, config) -> int:
    return _consecutive_excess(facts, facts.faculty_occupancy(), config.max_periods)


def student_max_consecutive(facts: TimetableFacts, config) -> int:
    return _consecutive_excess(facts, facts.leaf_occupancy(), config.max_periods)


# ---------------------------------------------------------------------------
# Soft
# ---------------------------------------------------------------------------


def student_gaps(facts: TimetableFacts, _config=None) -> int:
    return sum(_gaps(periods) for periods in facts.leaf_occupancy().values())


def student_min_free_periods(facts: TimetableFacts, config) -> int:
    return sum(
        max(0, config.min_free - (facts.periods_per_day - len(periods)))
        for periods in facts.leaf_occupancy().values()
        if periods
    )


def subject_spreading(facts: TimetableFacts, _config=None) -> int:
    counts = Counter(
        (p.session.subject_id, p.session.academic_group_id, p.day) for p in facts.placements
    )
    return sum(max(0, count - 1) for count in counts.values())


def faculty_workload_balance(facts: TimetableFacts, _config=None) -> int:
    hours: dict[int, int] = defaultdict(int)
    for placement in facts.placements:
        hours[placement.session.faculty_id] += placement.session.duration_periods
    capacities = facts.config.hard.faculty_weekly_cap.hours.as_dict()
    workloads = [
        FacultyWorkload(faculty_id, designation, hours.get(faculty_id, 0))
        for faculty_id, designation in (facts.timetable_input.faculty_designations or {}).items()
    ]
    return calculate_s2_penalty(workloads, capacities=capacities)


def faculty_max_lectures_per_day(facts: TimetableFacts, config) -> int:
    counts = Counter(
        (p.session.faculty_id, p.day)
        for p in facts.placements
        if p.session.subject_type is not None and p.session.subject_type.value == "LECTURE"
    )
    return sum(max(0, count - config.max_lectures) for count in counts.values())


def faculty_time_preference(facts: TimetableFacts, config) -> int:
    preferences = facts.timetable_input.faculty_time_preferences or {}
    ranges = config.ranges.as_dict()
    total = 0
    for placement in facts.placements:
        preference = preferences.get(placement.session.faculty_id, "ANY")
        if preference == "ANY":
            continue
        if preference not in ranges:
            raise ValueError(f"Unknown faculty time preference: {preference!r}")
        total += sum(1 for period in placement.occupied_periods if period not in ranges[preference])
    return total


def avoid_periods(facts: TimetableFacts, config) -> int:
    total = 0
    for placement in facts.placements:
        subject_type = placement.session.subject_type
        for rule in config.rules:
            if rule.subject_types and (
                subject_type is None or subject_type.value not in rule.subject_types
            ):
                continue
            if rule.days and placement.day.value not in rule.days:
                continue
            if rule.period in placement.occupied_periods:
                total += rule.penalty
    return total


def faculty_gaps(facts: TimetableFacts, _config=None) -> int:
    return sum(_gaps(periods) for periods in facts.faculty_occupancy().values())


def room_stability(facts: TimetableFacts, _config=None) -> int:
    rooms: dict[tuple[int, Day], set[int]] = defaultdict(set)
    for placement in facts.placements:
        room = facts.room_of(placement)
        if room is not None:
            rooms[(placement.session.academic_group_id, placement.day)].add(room.id)
    return sum(len(used) - 1 for used in rooms.values() if used)


def subject_day_spacing(facts: TimetableFacts, _config=None) -> int:
    used: dict[tuple[int, int], set[Day]] = defaultdict(set)
    for placement in facts.placements:
        used[(placement.session.subject_id, placement.session.academic_group_id)].add(placement.day)
    ordered = sorted(facts.timetable_input.days, key=lambda day: _WEEKDAY_ORDER[day])
    pairs = [
        (first, second)
        for first, second in zip(ordered, ordered[1:], strict=False)
        if _WEEKDAY_ORDER[second] - _WEEKDAY_ORDER[first] == 1
    ]
    return sum(
        1 for days in used.values() for first, second in pairs if first in days and second in days
    )


def group_daily_load_balance(facts: TimetableFacts, _config=None) -> int:
    occupancy = facts.leaf_occupancy()
    leaves = {leaf for leaf, _ in occupancy}
    total = 0
    for leaf in leaves:
        loads = [len(occupancy.get((leaf, day), ())) for day in facts.timetable_input.days]
        total += max(loads) - min(loads)
    return total


def parallel_batch_labs(facts: TimetableFacts, _config=None) -> int:
    occupancy = facts.leaf_occupancy()
    active = {leaf for leaf, _ in occupancy}
    hierarchy = facts.hierarchy
    total = 0

    for group_id in hierarchy.group_ids:
        children = hierarchy.children(group_id)
        if len(children) < 2:
            continue
        child_leaves = [hierarchy.leaves_of(child) for child in children]
        if not all(any(leaf in active for leaf in leaves) for leaves in child_leaves):
            continue
        for day in facts.timetable_input.days:
            for period in range(1, facts.periods_per_day + 1):
                busy = [
                    any(period in occupancy.get((leaf, day), ()) for leaf in leaves)
                    for leaves in child_leaves
                ]
                if any(busy) and not all(busy):
                    total += 1
    return total


def room_size_fit(facts: TimetableFacts, config) -> int:
    capacities = facts.timetable_input.academic_group_capacities or {}
    total = 0
    for placement in facts.placements:
        room = facts.room_of(placement)
        size = capacities.get(placement.session.academic_group_id)
        if room is None or size is None:
            continue
        total += max(0, (room.capacity - size) // config.waste_unit)
    return total


def faculty_compact_days(facts: TimetableFacts, _config=None) -> int:
    return len({(p.session.faculty_id, p.day) for p in facts.placements})


def consistent_subject_time(facts: TimetableFacts, _config=None) -> int:
    starts: dict[tuple[int, int], set[int]] = defaultdict(set)
    for placement in facts.placements:
        starts[(placement.session.subject_id, placement.session.academic_group_id)].add(
            placement.start_period
        )
    return sum(len(used) - 1 for used in starts.values())


def faculty_daily_load(facts: TimetableFacts, config) -> int:
    return sum(
        max(0, len(periods) - config.max_periods) for periods in facts.faculty_occupancy().values()
    )


def online_at_day_edges(facts: TimetableFacts, _config=None) -> int:
    in_person = facts.leaf_occupancy(in_person_only=True)
    total = 0
    for placement in facts.placements:
        if facts.room_of(placement) is not None:
            continue
        for leaf in facts.hierarchy.leaves_of(placement.session.academic_group_id):
            periods = in_person.get((leaf, placement.day), set())
            if any(p < placement.start_period for p in periods) and any(
                p > placement.end_period for p in periods
            ):
                total += 1
                break
    return total


def faculty_preferred_day_off(facts: TimetableFacts, _config=None) -> int:
    days_off = facts.timetable_input.faculty_preferred_day_off or {}
    return sum(
        placement.session.duration_periods
        for placement in facts.placements
        if days_off.get(placement.session.faculty_id) == placement.day
    )


def stability_vs_previous(facts: TimetableFacts, config) -> int:
    previous = facts.timetable_input.previous_placements or {}
    total = 0
    for placement in facts.placements:
        prior = previous.get(placement.session.id)
        if prior is None:
            continue
        if placement.day != prior.day or placement.start_period != prior.start_period:
            total += 1
        room = facts.room_of(placement)
        room_id = room.id if room is not None else None
        if config.room_change_penalty and room_id != prior.room_id:
            total += config.room_change_penalty
    return total


CALCULATORS: dict[str, Callable[[TimetableFacts, object], int]] = {
    "no_session_across_lunch": lunch_crossings,
    "faculty_max_consecutive": faculty_max_consecutive,
    "student_max_consecutive": student_max_consecutive,
    "student_gaps": student_gaps,
    "student_min_free_periods": student_min_free_periods,
    "subject_spreading": subject_spreading,
    "faculty_workload_balance": faculty_workload_balance,
    "faculty_max_lectures_per_day": faculty_max_lectures_per_day,
    "faculty_time_preference": faculty_time_preference,
    "avoid_periods": avoid_periods,
    "faculty_gaps": faculty_gaps,
    "room_stability": room_stability,
    "subject_day_spacing": subject_day_spacing,
    "group_daily_load_balance": group_daily_load_balance,
    "parallel_batch_labs": parallel_batch_labs,
    "room_size_fit": room_size_fit,
    "faculty_compact_days": faculty_compact_days,
    "consistent_subject_time": consistent_subject_time,
    "faculty_daily_load": faculty_daily_load,
    "online_at_day_edges": online_at_day_edges,
    "faculty_preferred_day_off": faculty_preferred_day_off,
    "stability_vs_previous": stability_vs_previous,
}


def constraint_config(config: TimetableConfig, key: str):
    if hasattr(config.soft, key):
        return getattr(config.soft, key)
    return getattr(config.constraints, key)


def calculate_penalty(
    key: str,
    timetable: Timetable,
    timetable_input: TimetableInput,
    config: TimetableConfig,
    facts: TimetableFacts | None = None,
) -> int:
    facts = facts or TimetableFacts.build(timetable, timetable_input, config)
    return CALCULATORS[key](facts, constraint_config(config, key))


def calculate_all_penalties(
    timetable: Timetable,
    timetable_input: TimetableInput,
    config: TimetableConfig,
) -> dict[str, int]:
    """Raw penalty of every constraint, whether enabled or not."""

    facts = TimetableFacts.build(timetable, timetable_input, config)
    return {
        key: calculator(facts, constraint_config(config, key))
        for key, calculator in CALCULATORS.items()
    }


def constraint_mode(config: TimetableConfig, key: str) -> tuple[str, int]:
    """Return ``(mode, weight)`` for reporting: off / soft / hard."""

    item = constraint_config(config, key)
    if hasattr(item, "mode"):
        weight = item.weight if item.mode == ConstraintMode.SOFT else 0
        return item.mode.value, weight
    return ("soft" if item.enabled else "off"), (item.weight if item.enabled else 0)
