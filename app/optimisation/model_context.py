"""Shared CP-SAT model state.

Everything that several constraints need is built here once, in a single
pass over the candidates:

* one Boolean per (session, candidate) with ``exactly_one`` per session;
* occupancy indexes ``faculty_slot``, ``room_slot`` and ``population_slot``
  mapping ``(entity, day, period)`` to the candidate variables covering it;
* Boolean busy variables ``faculty_busy``, ``group_busy`` (per leaf
  population) and ``room_busy``, each equal to the sum of its covering
  candidates. Because they are Boolean this also enforces "at most one"
  per slot, which replaces the former pairwise overlap clauses.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from app.core.timetable_config import TimetableConfig
from app.domain.calendar import DEFAULT_PERIOD_TIMES, Day
from app.domain.populations import GroupHierarchy
from app.domain.problem import SchedulingProblem
from app.domain.scheduling_candidate import SchedulingCandidate
from app.domain.timetable import SchedulingSession, TimetableInput

SlotKey = tuple[int, Day, int]


@dataclass(frozen=True)
class CandidateEntry:
    session_id: str
    index: int
    candidate: SchedulingCandidate
    var: cp_model.IntVar

    @property
    def session(self) -> SchedulingSession:
        return self.candidate.placement.session


@dataclass
class ModelContext:
    model: cp_model.CpModel
    problem: SchedulingProblem
    config: TimetableConfig
    domains: dict[str, tuple[SchedulingCandidate, ...]]
    hierarchy: GroupHierarchy
    candidate_vars: dict[str, list[cp_model.IntVar]] = field(default_factory=dict)
    entries: list[CandidateEntry] = field(default_factory=list)

    faculty_slot: dict[SlotKey, list[cp_model.IntVar]] = field(default_factory=dict)
    room_slot: dict[SlotKey, list[cp_model.IntVar]] = field(default_factory=dict)
    population_slot: dict[SlotKey, list[cp_model.IntVar]] = field(default_factory=dict)

    faculty_busy: dict[SlotKey, cp_model.IntVar] = field(default_factory=dict)
    group_busy: dict[SlotKey, cp_model.IntVar] = field(default_factory=dict)
    room_busy: dict[SlotKey, cp_model.IntVar] = field(default_factory=dict)

    faculty_ids: tuple[int, ...] = ()
    leaf_ids: tuple[int, ...] = ()
    room_ids: tuple[int, ...] = ()

    _cache: dict[str, object] = field(default_factory=dict)

    # -- calendar -------------------------------------------------------------

    @property
    def timetable_input(self) -> TimetableInput:
        return self.problem.timetable_input

    @property
    def days(self) -> tuple[Day, ...]:
        return self.timetable_input.days

    @property
    def periods(self) -> tuple[int, ...]:
        return tuple(range(1, self.timetable_input.periods_per_day + 1))

    @property
    def period_times(self) -> dict[int, tuple[int, int]]:
        return self.timetable_input.period_times or DEFAULT_PERIOD_TIMES

    def half_days(self) -> list[tuple[int, ...]]:
        """Contiguous period blocks separated by lunch (one block if no lunch)."""

        lunch = self.timetable_input.lunch_after_period
        periods = self.periods

        if lunch is None or not (1 <= lunch < len(periods)):
            return [periods]

        return [periods[:lunch], periods[lunch:]]

    # -- busy rows ------------------------------------------------------------

    def faculty_row(self, faculty_id: int, day: Day) -> list[cp_model.IntVar]:
        return [self.faculty_busy[(faculty_id, day, period)] for period in self.periods]

    def group_row(self, leaf_id: int, day: Day) -> list[cp_model.IntVar]:
        return [self.group_busy[(leaf_id, day, period)] for period in self.periods]

    def leaves_of_session(self, session: SchedulingSession) -> tuple[int, ...]:
        return self.hierarchy.leaves_of(session.academic_group_id)

    def has_candidates(self, index: dict[SlotKey, list], entity: int, day: Day) -> bool:
        return any((entity, day, period) in index for period in self.periods)

    # -- memoised shared structures ------------------------------------------

    def cached(self, key: str, factory: Callable[[], object]):
        if key not in self._cache:
            self._cache[key] = factory()
        return self._cache[key]

    def entries_by(self, key: str, keyfunc: Callable[[CandidateEntry], object]):
        """Group candidate entries by ``keyfunc`` (memoised under ``key``)."""

        def build() -> dict[object, list[CandidateEntry]]:
            grouped: dict[object, list[CandidateEntry]] = defaultdict(list)
            for entry in self.entries:
                grouped_key = keyfunc(entry)
                if grouped_key is not None:
                    grouped[grouped_key].append(entry)
            return grouped

        return self.cached(f"entries_by:{key}", build)

    def subject_day_used(self) -> dict[tuple[int, int, Day], cp_model.IntVar]:
        """``day_used[subject, group, day]``: any session of the subject held that day."""

        def build() -> dict[tuple[int, int, Day], cp_model.IntVar]:
            grouped = self.entries_by(
                "subject_group_day",
                lambda entry: (
                    entry.session.subject_id,
                    entry.session.academic_group_id,
                    entry.candidate.placement.day,
                ),
            )
            result = {}
            for (subject_id, group_id, day), items in grouped.items():
                used = self.model.new_bool_var(f"subject_day_used:{subject_id}:{group_id}:{day}")
                self.model.add_max_equality(used, [item.var for item in items])
                result[(subject_id, group_id, day)] = used
            return result

        return self.cached("subject_day_used", build)

    def faculty_day_used(self) -> dict[tuple[int, Day], cp_model.IntVar]:
        def build() -> dict[tuple[int, Day], cp_model.IntVar]:
            result = {}
            for faculty_id in self.faculty_ids:
                for day in self.days:
                    if not self.has_candidates(self.faculty_slot, faculty_id, day):
                        continue
                    used = self.model.new_bool_var(f"faculty_day_used:{faculty_id}:{day}")
                    self.model.add_max_equality(used, self.faculty_row(faculty_id, day))
                    result[(faculty_id, day)] = used
            return result

        return self.cached("faculty_day_used", build)

    # -- helpers --------------------------------------------------------------

    def linear_cost(
        self, costs: Iterable[tuple[int, cp_model.IntVar]], name: str
    ) -> cp_model.IntVar:
        """Create ``name == sum(cost * var)`` for non-negative per-candidate costs."""

        terms = [(cost, var) for cost, var in costs if cost]
        upper = sum(cost for cost, _ in terms)
        penalty = self.model.new_int_var(0, max(upper, 0), name)
        if terms:
            self.model.add(penalty == sum(cost * var for cost, var in terms))
        else:
            self.model.add(penalty == 0)
        return penalty

    def total(self, terms: list[cp_model.IntVar], upper: int, name: str) -> cp_model.IntVar:
        penalty = self.model.new_int_var(0, max(upper, 0), name)
        if terms:
            self.model.add(penalty == sum(terms))
        else:
            self.model.add(penalty == 0)
        return penalty


def build_model_context(
    problem: SchedulingProblem,
    domains: dict[str, tuple[SchedulingCandidate, ...]],
    config: TimetableConfig,
    hierarchy: GroupHierarchy,
    model: cp_model.CpModel | None = None,
) -> ModelContext:
    """Create candidate variables, occupancy indexes and busy variables."""

    model = model or cp_model.CpModel()
    context = ModelContext(
        model=model,
        problem=problem,
        config=config,
        domains=domains,
        hierarchy=hierarchy,
    )

    faculty_slot: dict[SlotKey, list[cp_model.IntVar]] = defaultdict(list)
    room_slot: dict[SlotKey, list[cp_model.IntVar]] = defaultdict(list)
    population_slot: dict[SlotKey, list[cp_model.IntVar]] = defaultdict(list)

    for session_id, candidates in domains.items():
        variables = [
            model.new_bool_var(f"x:{session_id}:{index}") for index in range(len(candidates))
        ]
        model.add_exactly_one(variables)
        context.candidate_vars[session_id] = variables

        for index, (candidate, var) in enumerate(zip(candidates, variables, strict=True)):
            context.entries.append(CandidateEntry(session_id, index, candidate, var))

            placement = candidate.placement
            session = placement.session
            leaves = hierarchy.leaves_of(session.academic_group_id)

            for period in placement.occupied_periods:
                faculty_slot[(session.faculty_id, placement.day, period)].append(var)

                for leaf in leaves:
                    population_slot[(leaf, placement.day, period)].append(var)

                if candidate.room is not None:
                    room_slot[(candidate.room.id, placement.day, period)].append(var)

    context.faculty_slot = dict(faculty_slot)
    context.room_slot = dict(room_slot)
    context.population_slot = dict(population_slot)

    context.faculty_ids = tuple(sorted({key[0] for key in faculty_slot}))
    context.leaf_ids = tuple(sorted({key[0] for key in population_slot}))
    context.room_ids = tuple(sorted({key[0] for key in room_slot}))

    context.faculty_busy = _busy_variables(
        model, "faculty_busy", context.faculty_ids, context.days, context.periods, faculty_slot
    )
    context.group_busy = _busy_variables(
        model, "group_busy", context.leaf_ids, context.days, context.periods, population_slot
    )
    context.room_busy = _busy_variables(
        model, "room_busy", context.room_ids, context.days, context.periods, room_slot
    )

    return context


def _busy_variables(
    model: cp_model.CpModel,
    prefix: str,
    entity_ids: tuple[int, ...],
    days: tuple[Day, ...],
    periods: tuple[int, ...],
    index: dict[SlotKey, list[cp_model.IntVar]],
) -> dict[SlotKey, cp_model.IntVar]:
    busy: dict[SlotKey, cp_model.IntVar] = {}

    for entity_id in entity_ids:
        for day in days:
            for period in periods:
                key = (entity_id, day, period)
                covering = index.get(key)

                if not covering:
                    busy[key] = model.new_constant(0)
                    continue

                var = model.new_bool_var(f"{prefix}:{entity_id}:{day}:{period}")

                if len(covering) > 1:
                    model.add_at_most_one(covering)

                model.add(var == sum(covering))
                busy[key] = var

    return busy
