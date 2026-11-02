"""CP-SAT builders for configurable constraints.

Every builder reads the shared :class:`ModelContext` (occupancy indexes and
busy variables) and returns a named ``IntVar`` holding its raw penalty, so
the value can be reported and compared with the independent calculator in
``app.optimisation.penalties``.

Builders are only called for enabled constraints, so a disabled constraint
adds no variables to the model.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from ortools.sat.python import cp_model

from app.core.timetable_config import (
    AvoidPeriodsConfig,
    ConstraintMode,
    DailyLoadConfig,
    MaxConsecutiveConfig,
    MaxLecturesConfig,
    MinFreeConfig,
    RoomSizeFitConfig,
    SoftConfig,
    StabilityConfig,
    TimePreferenceConfig,
)
from app.domain.calendar import Day
from app.domain.candidates import crosses_lunch
from app.optimisation.faculty_workload import FacultyWorkload, calculate_s2_penalty
from app.optimisation.model_context import ModelContext
from app.optimisation.objectives import (
    add_excess,
    add_gap_penalty,
    add_prefix_suffix,
    build_spreading_penalty,
)

_WEEKDAY_ORDER = {day: index for index, day in enumerate(Day)}


@dataclass(frozen=True)
class PenaltyTerm:
    key: str
    kind: str  # "soft" or "flexible"
    weight: int
    var: cp_model.IntVar


# ===========================================================================
# Optional hard constraints
# ===========================================================================


def add_faculty_daily_span(context: ModelContext, max_minutes: int) -> None:
    """Earliest start to latest end per faculty/day must be <= ``max_minutes``.

    Periods are contiguous time blocks, so it is enough to forbid every
    pair of periods (p, q) whose combined span is too long.
    """

    times = context.period_times
    periods = context.periods
    model = context.model

    forbidden_pairs = [
        (first, second)
        for first in periods
        for second in periods
        if first <= second and times[second][1] - times[first][0] > max_minutes
    ]

    if not forbidden_pairs:
        return

    for faculty_id in context.faculty_ids:
        for day in context.days:
            if not context.has_candidates(context.faculty_slot, faculty_id, day):
                continue
            for first, second in forbidden_pairs:
                first_busy = context.faculty_busy[(faculty_id, day, first)]
                if first == second:
                    model.add(first_busy == 0)
                    continue
                second_busy = context.faculty_busy[(faculty_id, day, second)]
                model.add(first_busy + second_busy <= 1)


def _faculty_hour_terms(context: ModelContext) -> dict[int, list]:
    terms: dict[int, list] = defaultdict(list)
    for entry in context.entries:
        terms[entry.session.faculty_id].append(entry.session.duration_periods * entry.var)
    return terms


def add_faculty_weekly_cap(context: ModelContext) -> None:
    designations = context.timetable_input.faculty_designations or {}
    hours = context.config.hard.faculty_weekly_cap.hours

    for faculty_id, terms in _faculty_hour_terms(context).items():
        designation = designations.get(faculty_id)
        if designation is None:
            continue
        cap = hours.for_designation(designation)
        if cap is not None:
            context.model.add(sum(terms) <= cap)


def add_faculty_weekly_minimum(context: ModelContext) -> None:
    designations = context.timetable_input.faculty_designations or {}
    hours = context.config.hard.faculty_weekly_minimum.hours
    terms_by_faculty = _faculty_hour_terms(context)

    for faculty_id, designation in designations.items():
        minimum = hours.for_designation(designation)
        if minimum is None:
            continue
        terms = terms_by_faculty.get(faculty_id, [])
        if terms:
            context.model.add(sum(terms) >= minimum)
        elif minimum > 0:
            # No sessions at all: the minimum cannot be met (pre-solve reports this).
            context.model.add_bool_or([])


# ===========================================================================
# Flexible constraints
# ===========================================================================


def build_lunch_penalty(context: ModelContext, config) -> cp_model.IntVar:
    """Soft mode of ``no_session_across_lunch``: 1 per crossing session."""

    lunch = context.timetable_input.lunch_after_period
    costs = (
        (1, entry.var)
        for entry in context.entries
        if not entry.session.allow_across_lunch and crosses_lunch(entry.candidate.placement, lunch)
    )
    return context.linear_cost(costs, "pen:no_session_across_lunch")


def _consecutive_windows(context: ModelContext, size: int) -> list[tuple[int, ...]]:
    windows = []
    for block in context.half_days():
        for start in range(0, len(block) - size + 1):
            windows.append(block[start : start + size])
    return windows


def _max_consecutive(
    context: ModelContext,
    config: MaxConsecutiveConfig,
    *,
    key: str,
    entity_ids: tuple[int, ...],
    busy: dict,
    index: dict,
) -> cp_model.IntVar | None:
    limit = config.max_periods
    windows = _consecutive_windows(context, limit + 1)
    model = context.model
    excesses: list[cp_model.IntVar] = []

    for entity_id in entity_ids:
        for day in context.days:
            if not context.has_candidates(index, entity_id, day):
                continue
            for window in windows:
                total = sum(busy[(entity_id, day, period)] for period in window)
                if config.mode == ConstraintMode.HARD:
                    model.add(total <= limit)
                else:
                    excesses.append(
                        add_excess(
                            model,
                            total,
                            limit,
                            len(window),
                            f"pen:{key}:{entity_id}:{day}:{window[0]}",
                        )
                    )

    if config.mode == ConstraintMode.HARD:
        return None

    return context.total(excesses, len(excesses), f"pen:{key}")


def build_faculty_max_consecutive(context: ModelContext, config: MaxConsecutiveConfig):
    return _max_consecutive(
        context,
        config,
        key="faculty_max_consecutive",
        entity_ids=context.faculty_ids,
        busy=context.faculty_busy,
        index=context.faculty_slot,
    )


def build_student_max_consecutive(context: ModelContext, config: MaxConsecutiveConfig):
    return _max_consecutive(
        context,
        config,
        key="student_max_consecutive",
        entity_ids=context.leaf_ids,
        busy=context.group_busy,
        index=context.population_slot,
    )


# ===========================================================================
# Soft constraints
# ===========================================================================


def build_student_gaps(context: ModelContext, config: SoftConfig) -> cp_model.IntVar:
    """S1: idle periods inside each leaf population's day (includes parent sessions)."""

    rows = {
        (leaf, day): context.group_row(leaf, day)
        for leaf in context.leaf_ids
        for day in context.days
        if context.has_candidates(context.population_slot, leaf, day)
    }
    return add_gap_penalty(context.model, rows, "pen:student_gaps")


def build_student_min_free_periods(context: ModelContext, config: MinFreeConfig):
    """S14: per leaf/day, ``max(0, min_free - free periods)``."""

    periods_per_day = len(context.periods)
    threshold = max(0, periods_per_day - config.min_free)
    excesses = []

    for leaf in context.leaf_ids:
        for day in context.days:
            if not context.has_candidates(context.population_slot, leaf, day):
                continue
            excesses.append(
                add_excess(
                    context.model,
                    sum(context.group_row(leaf, day)),
                    threshold,
                    periods_per_day,
                    f"pen:student_min_free_periods:{leaf}:{day}",
                )
            )

    return context.total(excesses, len(excesses) * config.min_free, "pen:student_min_free_periods")


def build_subject_spreading(context: ModelContext, config: SoftConfig) -> cp_model.IntVar:
    """S4: extra sessions of a subject for a group on the same day."""

    occurrences = {
        key: [entry.var for entry in entries]
        for key, entries in context.entries_by(
            "subject_group_day",
            lambda entry: (
                entry.session.subject_id,
                entry.session.academic_group_id,
                entry.candidate.placement.day,
            ),
        ).items()
    }
    return build_spreading_penalty(
        context.model,
        occurrences,
        context.subject_day_used(),
        "pen:subject_spreading",
    )


def build_faculty_workload_balance(context: ModelContext, config: SoftConfig):
    """S2: pairwise utilisation differences within each designation.

    Every session is placed exactly once and its faculty is fixed by the
    teaching assignment, so weekly hours (and therefore S2) are constant
    for a given input. The penalty is computed directly instead of adding
    O(n^2) helper variables; it becomes a decision-dependent term only if
    faculty assignment is ever made part of the model.
    """

    workloads = workloads_from_sessions(context)
    value = calculate_s2_penalty(
        workloads,
        capacities=context.config.hard.faculty_weekly_cap.hours.as_dict(),
    )
    return context.model.new_int_var(value, value, "pen:faculty_workload_balance")


def workloads_from_sessions(context: ModelContext) -> list[FacultyWorkload]:
    hours: dict[int, int] = defaultdict(int)
    for session in context.timetable_input.sessions:
        hours[session.faculty_id] += session.duration_periods
    return [
        FacultyWorkload(faculty_id, designation, hours.get(faculty_id, 0))
        for faculty_id, designation in (context.timetable_input.faculty_designations or {}).items()
    ]


def build_faculty_max_lectures_per_day(context: ModelContext, config: MaxLecturesConfig):
    """S11: lectures beyond ``max_lectures`` per faculty/day."""

    grouped = context.entries_by(
        "lecture_faculty_day",
        lambda entry: (
            (entry.session.faculty_id, entry.candidate.placement.day)
            if entry.session.subject_type is not None
            and entry.session.subject_type.value == "LECTURE"
            else None
        ),
    )

    excesses = []
    upper = 0

    for (faculty_id, day), entries in sorted(grouped.items(), key=lambda item: str(item[0])):
        count = len({entry.session_id for entry in entries})
        if count <= config.max_lectures:
            continue
        excesses.append(
            add_excess(
                context.model,
                sum(entry.var for entry in entries),
                config.max_lectures,
                count,
                f"pen:faculty_max_lectures_per_day:{faculty_id}:{day}",
            )
        )
        upper += count - config.max_lectures

    return context.total(excesses, upper, "pen:faculty_max_lectures_per_day")


def build_faculty_time_preference(context: ModelContext, config: TimePreferenceConfig):
    """S3: occupied periods outside the faculty member's preferred range."""

    preferences = context.timetable_input.faculty_time_preferences or {}
    ranges = config.ranges.as_dict()

    def cost(entry) -> int:
        preference = preferences.get(entry.session.faculty_id, "ANY")
        if preference == "ANY":
            return 0
        if preference not in ranges:
            raise ValueError(f"Unknown faculty time preference: {preference!r}")
        preferred = ranges[preference]
        return sum(
            1 for period in entry.candidate.placement.occupied_periods if period not in preferred
        )

    return context.linear_cost(
        ((cost(entry), entry.var) for entry in context.entries),
        "pen:faculty_time_preference",
    )


def avoid_period_cost(placement, rules) -> int:
    subject_type = placement.session.subject_type
    total = 0
    for rule in rules:
        if rule.subject_types and (
            subject_type is None or subject_type.value not in rule.subject_types
        ):
            continue
        if rule.days and placement.day.value not in rule.days:
            continue
        if rule.period in placement.occupied_periods:
            total += rule.penalty
    return total


def build_avoid_periods(context: ModelContext, config: AvoidPeriodsConfig):
    return context.linear_cost(
        (
            (avoid_period_cost(entry.candidate.placement, config.rules), entry.var)
            for entry in context.entries
        ),
        "pen:avoid_periods",
    )


def build_faculty_gaps(context: ModelContext, config: SoftConfig):
    rows = {
        (faculty_id, day): context.faculty_row(faculty_id, day)
        for faculty_id in context.faculty_ids
        for day in context.days
        if context.has_candidates(context.faculty_slot, faculty_id, day)
    }
    return add_gap_penalty(context.model, rows, "pen:faculty_gaps")


def build_room_stability(context: ModelContext, config: SoftConfig):
    """Per group/day: distinct rooms used - 1 (0 without in-person classes)."""

    model = context.model
    grouped = context.entries_by(
        "group_day_room",
        lambda entry: (
            (
                entry.session.academic_group_id,
                entry.candidate.placement.day,
                entry.candidate.room.id,
            )
            if entry.candidate.room is not None
            else None
        ),
    )

    rooms_by_group_day: dict[tuple, list[cp_model.IntVar]] = defaultdict(list)

    for (group_id, day, room_id), entries in grouped.items():
        used = model.new_bool_var(f"room_used:{group_id}:{day}:{room_id}")
        model.add_max_equality(used, [entry.var for entry in entries])
        rooms_by_group_day[(group_id, day)].append(used)

    penalties = []
    upper = 0

    for (group_id, day), used_rooms in rooms_by_group_day.items():
        if len(used_rooms) < 2:
            continue
        day_used = model.new_bool_var(f"room_day_used:{group_id}:{day}")
        model.add_max_equality(day_used, used_rooms)
        penalty = model.new_int_var(0, len(used_rooms) - 1, f"pen:room_stability:{group_id}:{day}")
        model.add(penalty == sum(used_rooms) - day_used)
        penalties.append(penalty)
        upper += len(used_rooms) - 1

    return context.total(penalties, upper, "pen:room_stability")


def adjacent_day_pairs(days) -> list[tuple[Day, Day]]:
    ordered = sorted(days, key=lambda day: _WEEKDAY_ORDER[day])
    return [
        (first, second)
        for first, second in zip(ordered, ordered[1:], strict=False)
        if _WEEKDAY_ORDER[second] - _WEEKDAY_ORDER[first] == 1
    ]


def build_subject_day_spacing(context: ModelContext, config: SoftConfig):
    """1 per adjacent calendar-day pair on which the same subject meets the same group."""

    model = context.model
    day_used = context.subject_day_used()
    pairs = adjacent_day_pairs(context.days)
    subject_groups = sorted({(subject_id, group_id) for subject_id, group_id, _ in day_used})
    penalties = []

    for subject_id, group_id in subject_groups:
        for first, second in pairs:
            a = day_used.get((subject_id, group_id, first))
            b = day_used.get((subject_id, group_id, second))
            if a is None or b is None:
                continue
            both = model.new_bool_var(f"pen:subject_day_spacing:{subject_id}:{group_id}:{first}")
            model.add_min_equality(both, [a, b])
            penalties.append(both)

    return context.total(penalties, len(penalties), "pen:subject_day_spacing")


def build_group_daily_load_balance(context: ModelContext, config: SoftConfig):
    """Per leaf population: max(day load) - min(day load) over configured days."""

    model = context.model
    periods_per_day = len(context.periods)
    penalties = []

    for leaf in context.leaf_ids:
        loads = []
        for day in context.days:
            load = model.new_int_var(0, periods_per_day, f"group_load:{leaf}:{day}")
            model.add(load == sum(context.group_row(leaf, day)))
            loads.append(load)
        highest = model.new_int_var(0, periods_per_day, f"group_load_max:{leaf}")
        lowest = model.new_int_var(0, periods_per_day, f"group_load_min:{leaf}")
        model.add_max_equality(highest, loads)
        model.add_min_equality(lowest, loads)
        penalty = model.new_int_var(0, periods_per_day, f"pen:group_daily_load_balance:{leaf}")
        model.add(penalty == highest - lowest)
        penalties.append(penalty)

    return context.total(
        penalties, len(penalties) * periods_per_day, "pen:group_daily_load_balance"
    )


def parallel_batch_parents(context_hierarchy, active_leaves: set[int]) -> list[tuple[int, list]]:
    """Parents with >= 2 children whose populations all have sessions."""

    parents = []
    for group_id in context_hierarchy.group_ids:
        children = context_hierarchy.children(group_id)
        if len(children) < 2:
            continue
        child_leaves = [context_hierarchy.leaves_of(child) for child in children]
        if all(any(leaf in active_leaves for leaf in leaves) for leaves in child_leaves):
            parents.append((group_id, child_leaves))
    return parents


def build_parallel_batch_labs(context: ModelContext, config: SoftConfig):
    """Per parent/day/period: any batch busy - all batches busy."""

    model = context.model
    active = set(context.leaf_ids)
    penalties = []

    for parent_id, child_leaves in parallel_batch_parents(context.hierarchy, active):
        for day in context.days:
            for period in context.periods:
                if not any(
                    (leaf, day, period) in context.population_slot
                    for leaves in child_leaves
                    for leaf in leaves
                ):
                    continue

                child_busy = []
                for leaves in child_leaves:
                    row = [
                        context.group_busy[(leaf, day, period)] for leaf in leaves if leaf in active
                    ]
                    if len(row) == 1:
                        child_busy.append(row[0])
                    else:
                        busy = model.new_bool_var(
                            f"child_busy:{parent_id}:{leaves[0]}:{day}:{period}"
                        )
                        model.add_max_equality(busy, row)
                        child_busy.append(busy)

                any_busy = model.new_bool_var(f"batch_any:{parent_id}:{day}:{period}")
                all_busy = model.new_bool_var(f"batch_all:{parent_id}:{day}:{period}")
                model.add_max_equality(any_busy, child_busy)
                model.add_min_equality(all_busy, child_busy)
                penalty = model.new_bool_var(f"pen:parallel_batch_labs:{parent_id}:{day}:{period}")
                model.add(penalty == any_busy - all_busy)
                penalties.append(penalty)

    return context.total(penalties, len(penalties), "pen:parallel_batch_labs")


def room_size_cost(candidate, capacities: dict[int, int] | None, waste_unit: int) -> int:
    if candidate.room is None or not capacities:
        return 0
    group_size = capacities.get(candidate.placement.session.academic_group_id)
    if group_size is None:
        return 0
    return max(0, (candidate.room.capacity - group_size) // waste_unit)


def build_room_size_fit(context: ModelContext, config: RoomSizeFitConfig):
    capacities = context.timetable_input.academic_group_capacities
    return context.linear_cost(
        (
            (room_size_cost(entry.candidate, capacities, config.waste_unit), entry.var)
            for entry in context.entries
        ),
        "pen:room_size_fit",
    )


def build_faculty_compact_days(context: ModelContext, config: SoftConfig):
    used = list(context.faculty_day_used().values())
    return context.total(used, len(used), "pen:faculty_compact_days")


def build_consistent_subject_time(context: ModelContext, config: SoftConfig):
    """Per subject/group: distinct start periods - 1."""

    model = context.model
    grouped = context.entries_by(
        "subject_group_start",
        lambda entry: (
            entry.session.subject_id,
            entry.session.academic_group_id,
            entry.candidate.placement.start_period,
        ),
    )

    starts: dict[tuple[int, int], list[cp_model.IntVar]] = defaultdict(list)
    session_counts: dict[tuple[int, int], set[str]] = defaultdict(set)

    for (subject_id, group_id, start), entries in grouped.items():
        used = model.new_bool_var(f"start_used:{subject_id}:{group_id}:{start}")
        model.add_max_equality(used, [entry.var for entry in entries])
        starts[(subject_id, group_id)].append(used)
        session_counts[(subject_id, group_id)].update(entry.session_id for entry in entries)

    penalties = []
    upper = 0

    for key, used in starts.items():
        sessions = len(session_counts[key])
        if sessions < 2:
            continue
        bound = min(sessions, len(used)) - 1
        penalty = model.new_int_var(0, bound, f"pen:consistent_subject_time:{key[0]}:{key[1]}")
        model.add(penalty == sum(used) - 1)
        penalties.append(penalty)
        upper += bound

    return context.total(penalties, upper, "pen:consistent_subject_time")


def build_faculty_daily_load(context: ModelContext, config: DailyLoadConfig):
    excesses = []
    periods_per_day = len(context.periods)

    for faculty_id in context.faculty_ids:
        for day in context.days:
            if not context.has_candidates(context.faculty_slot, faculty_id, day):
                continue
            excesses.append(
                add_excess(
                    context.model,
                    sum(context.faculty_row(faculty_id, day)),
                    config.max_periods,
                    periods_per_day,
                    f"pen:faculty_daily_load:{faculty_id}:{day}",
                )
            )

    return context.total(
        excesses,
        len(excesses) * max(0, periods_per_day - config.max_periods),
        "pen:faculty_daily_load",
    )


def build_online_at_day_edges(context: ModelContext, config: SoftConfig):
    """1 per online session with an in-person class before and after it that day."""

    model = context.model
    online_entries = [entry for entry in context.entries if entry.candidate.room is None]

    if not online_entries:
        return context.total([], 0, "pen:online_at_day_edges")

    in_person: dict[tuple, list[cp_model.IntVar]] = defaultdict(list)

    for entry in context.entries:
        if entry.candidate.room is None:
            continue
        placement = entry.candidate.placement
        for leaf in context.leaves_of_session(entry.session):
            for period in placement.occupied_periods:
                in_person[(leaf, placement.day, period)].append(entry.var)

    needed_rows = {
        (leaf, entry.candidate.placement.day)
        for entry in online_entries
        for leaf in context.leaves_of_session(entry.session)
    }

    edges: dict[tuple, tuple[list, list]] = {}

    for leaf, day in needed_rows:
        row = []
        for period in context.periods:
            covering = in_person.get((leaf, day, period))
            if not covering:
                row.append(0)
                continue
            busy = model.new_bool_var(f"in_person_busy:{leaf}:{day}:{period}")
            model.add(busy == sum(covering))
            row.append(busy)
        if not any(not isinstance(item, int) for item in row):
            continue
        row_vars = [item if not isinstance(item, int) else model.new_constant(0) for item in row]
        edges[(leaf, day)] = add_prefix_suffix(model, row_vars, f"in_person:{leaf}:{day}")

    penalties = []

    for entry in online_entries:
        placement = entry.candidate.placement
        sandwiches = []
        for leaf in context.leaves_of_session(entry.session):
            row_edges = edges.get((leaf, placement.day))
            if row_edges is None:
                continue
            before, after = row_edges
            before_var = before[placement.start_period - 1]
            after_var = after[placement.end_period - 1]
            if isinstance(before_var, int) or isinstance(after_var, int):
                continue
            sandwich = model.new_bool_var(
                f"online_sandwich:{entry.session_id}:{entry.index}:{leaf}"
            )
            model.add_min_equality(sandwich, [entry.var, before_var, after_var])
            sandwiches.append(sandwich)

        if not sandwiches:
            continue
        if len(sandwiches) == 1:
            penalties.append(sandwiches[0])
            continue
        penalty = model.new_bool_var(f"online_sandwich:{entry.session_id}:{entry.index}")
        model.add_max_equality(penalty, sandwiches)
        penalties.append(penalty)

    online_sessions = len({entry.session_id for entry in online_entries})
    return context.total(penalties, online_sessions, "pen:online_at_day_edges")


def build_faculty_preferred_day_off(context: ModelContext, config: SoftConfig):
    days_off = context.timetable_input.faculty_preferred_day_off or {}
    return context.linear_cost(
        (
            (
                entry.session.duration_periods
                if days_off.get(entry.session.faculty_id) == entry.candidate.placement.day
                else 0,
                entry.var,
            )
            for entry in context.entries
        ),
        "pen:faculty_preferred_day_off",
    )


def stability_cost(candidate, previous, room_change_penalty: int) -> int:
    if previous is None:
        return 0
    placement = candidate.placement
    cost = 0
    if placement.day != previous.day or placement.start_period != previous.start_period:
        cost += 1
    room_id = candidate.room.id if candidate.room is not None else None
    if room_change_penalty and room_id != previous.room_id:
        cost += room_change_penalty
    return cost


def build_stability_vs_previous(context: ModelContext, config: StabilityConfig):
    previous = context.timetable_input.previous_placements or {}
    return context.linear_cost(
        (
            (
                stability_cost(
                    entry.candidate, previous.get(entry.session_id), config.room_change_penalty
                ),
                entry.var,
            )
            for entry in context.entries
        ),
        "pen:stability_vs_previous",
    )


SOFT_BUILDERS: dict[str, Callable[[ModelContext, SoftConfig], cp_model.IntVar]] = {
    "student_gaps": build_student_gaps,
    "student_min_free_periods": build_student_min_free_periods,
    "subject_spreading": build_subject_spreading,
    "faculty_workload_balance": build_faculty_workload_balance,
    "faculty_max_lectures_per_day": build_faculty_max_lectures_per_day,
    "faculty_time_preference": build_faculty_time_preference,
    "avoid_periods": build_avoid_periods,
    "faculty_gaps": build_faculty_gaps,
    "room_stability": build_room_stability,
    "subject_day_spacing": build_subject_day_spacing,
    "group_daily_load_balance": build_group_daily_load_balance,
    "parallel_batch_labs": build_parallel_batch_labs,
    "room_size_fit": build_room_size_fit,
    "faculty_compact_days": build_faculty_compact_days,
    "consistent_subject_time": build_consistent_subject_time,
    "faculty_daily_load": build_faculty_daily_load,
    "online_at_day_edges": build_online_at_day_edges,
    "faculty_preferred_day_off": build_faculty_preferred_day_off,
    "stability_vs_previous": build_stability_vs_previous,
}

FLEXIBLE_BUILDERS = {
    "faculty_max_consecutive": build_faculty_max_consecutive,
    "student_max_consecutive": build_student_max_consecutive,
}


def apply_constraints(context: ModelContext) -> list[PenaltyTerm]:
    """Add every enabled optional constraint and return the objective terms."""

    config = context.config
    terms: list[PenaltyTerm] = []

    # Optional hard constraints. Locks, group blocks and the hard lunch rule
    # are applied during candidate generation; role restrictions pre-solve.
    if config.hard.faculty_daily_span.enabled:
        add_faculty_daily_span(context, config.hard.faculty_daily_span.max_minutes)
    if config.hard.faculty_weekly_cap.enabled:
        add_faculty_weekly_cap(context)
    if config.hard.faculty_weekly_minimum.enabled:
        add_faculty_weekly_minimum(context)

    # Flexible constraints.
    lunch = config.constraints.no_session_across_lunch
    if lunch.mode == ConstraintMode.SOFT:
        terms.append(
            PenaltyTerm(
                "no_session_across_lunch",
                "flexible",
                lunch.weight,
                build_lunch_penalty(context, lunch),
            )
        )

    for key, builder in FLEXIBLE_BUILDERS.items():
        item = getattr(config.constraints, key)
        if item.mode == ConstraintMode.OFF:
            continue
        var = builder(context, item)
        if var is not None:
            terms.append(PenaltyTerm(key, "flexible", item.weight, var))

    # Soft constraints.
    for key, item in config.soft_items():
        if not item.enabled:
            continue
        terms.append(PenaltyTerm(key, "soft", item.weight, SOFT_BUILDERS[key](context, item)))

    return terms
