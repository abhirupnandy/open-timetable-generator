from __future__ import annotations

from collections import defaultdict
from collections.abc import Hashable, Sequence

from ortools.sat.python import cp_model

from app.domain.scheduling_candidate import SchedulingCandidate

# ---------------------------------------------------------------------------
# Reusable patterns
# ---------------------------------------------------------------------------


def _key_name(key: Hashable) -> str:
    if isinstance(key, tuple):
        return ":".join(str(part) for part in key)
    return str(key)


def add_prefix_suffix(
    model: cp_model.CpModel,
    occupied: Sequence[cp_model.IntVar],
    name: str,
) -> tuple[list, list]:
    """Return ``(before, after)`` lists for a row of occupancy Booleans.

    ``before[i]`` is 1 when any period strictly before index ``i`` is
    occupied; ``after[i]`` is 1 when any period strictly after ``i`` is.
    Built as chains, so each row costs O(periods) variables.
    """

    count = len(occupied)
    before: list = [0] * count
    after: list = [0] * count

    for index in range(1, count):
        if index == 1:
            before[index] = occupied[0]
            continue
        var = model.new_bool_var(f"{name}:before:{index + 1}")
        model.add_max_equality(var, [before[index - 1], occupied[index - 1]])
        before[index] = var

    for index in range(count - 2, -1, -1):
        if index == count - 2:
            after[index] = occupied[count - 1]
            continue
        var = model.new_bool_var(f"{name}:after:{index + 1}")
        model.add_max_equality(var, [after[index + 1], occupied[index + 1]])
        after[index] = var

    return before, after


def add_gap_penalty(
    model: cp_model.CpModel,
    rows: dict[Hashable, Sequence[cp_model.IntVar]],
    name: str,
) -> cp_model.IntVar:
    """Total number of idle periods between the first and last occupied period.

    ``rows`` maps an (entity, day) key to its ordered occupancy Booleans.
    ``gap = not occupied AND occupied-before AND occupied-after`` exactly.
    """

    gaps: list[cp_model.IntVar] = []

    for key, occupied in rows.items():
        if len(occupied) < 3:
            continue

        row_name = f"{name}:{_key_name(key)}"
        before, after = add_prefix_suffix(model, occupied, row_name)

        for index in range(1, len(occupied) - 1):
            gap = model.new_bool_var(f"{row_name}:gap:{index + 1}")
            model.add_min_equality(gap, [before[index], after[index], 1 - occupied[index]])
            gaps.append(gap)

    total = model.new_int_var(0, len(gaps), name)
    model.add(total == sum(gaps)) if gaps else model.add(total == 0)
    return total


def add_excess(
    model: cp_model.CpModel,
    expression,
    threshold: int,
    upper: int,
    name: str,
) -> cp_model.IntVar:
    """Create ``name == max(0, expression - threshold)``."""

    excess = model.new_int_var(0, max(0, upper - threshold), name)
    model.add_max_equality(excess, [expression - threshold, 0])
    return excess


# ---------------------------------------------------------------------------
# Legacy entry points (per academic group, built from candidate domains)
# ---------------------------------------------------------------------------


def _group_period_index(
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
) -> dict[tuple[int, object, int], list[cp_model.IntVar]]:
    index: dict[tuple[int, object, int], list[cp_model.IntVar]] = defaultdict(list)

    for session_id, candidates in candidate_domains.items():
        variables = candidate_variables[session_id]

        for candidate, variable in zip(candidates, variables, strict=True):
            placement = candidate.placement
            group_id = placement.session.academic_group_id

            for period in placement.occupied_periods:
                index[(group_id, placement.day, period)].append(variable)

    return index


def build_student_group_gap_objective(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    *,
    days,
    periods_per_day: int,
) -> cp_model.LinearExpr:
    """Return the total number of internal gaps per academic group and day.

    The occupancy index is built in a single pass over the candidates.
    The solver itself uses the leaf-population version in
    ``app.optimisation.constraints``.
    """

    index = _group_period_index(candidate_domains, candidate_variables)
    group_ids = sorted({key[0] for key in index})
    rows: dict[tuple[int, str], list[cp_model.IntVar]] = {}

    for group_id in group_ids:
        for day in days:
            row = []
            for period in range(1, periods_per_day + 1):
                covering = index.get((group_id, day, period), [])
                occupied = model.new_bool_var(
                    f"group:{group_id}:day:{day.value}:period:{period}:occupied"
                )
                if covering:
                    model.add(occupied == sum(covering))
                else:
                    model.add(occupied == 0)
                row.append(occupied)
            rows[(group_id, day.value)] = row

    return add_gap_penalty(model, rows, "s1_group_gaps")


def build_subject_spreading_objective(
    model: cp_model.CpModel,
    candidate_domains: dict[str, tuple[SchedulingCandidate, ...]],
    candidate_variables: dict[str, list[cp_model.IntVar]],
    *,
    days,
) -> cp_model.LinearExpr:
    """
    Return the S4 subject-spreading penalty.

    For each subject + academic group + day:

        penalty = number_of_sessions_on_day - day_used

    so one session on a day costs 0, two cost 1, three cost 2.
    A multi-period session is counted once.
    """

    occurrences: dict[tuple[int, int, object], list[cp_model.IntVar]] = defaultdict(list)
    allowed_days = set(days)

    for session_id, candidates in candidate_domains.items():
        for candidate, variable in zip(candidates, candidate_variables[session_id], strict=True):
            session = candidate.placement.session
            day = candidate.placement.day
            if day in allowed_days:
                occurrences[(session.subject_id, session.academic_group_id, day)].append(variable)

    return build_spreading_penalty(model, occurrences, {}, "s4_subject_spreading")


def build_spreading_penalty(
    model: cp_model.CpModel,
    occurrences: dict[tuple[int, int, object], list[cp_model.IntVar]],
    day_used: dict[tuple[int, int, object], cp_model.IntVar],
    name: str,
) -> cp_model.IntVar:
    """``sum(count - day_used)`` over subject/group/day keys."""

    penalties: list[cp_model.IntVar] = []
    upper = 0

    for key in sorted(occurrences, key=lambda item: (item[0], item[1], str(item[2]))):
        variables = occurrences[key]
        used = day_used.get(key)

        if used is None:
            used = model.new_bool_var(f"{name}:{_key_name(key)}:used")
            model.add_max_equality(used, variables)

        penalty = model.new_int_var(0, len(variables), f"{name}:{_key_name(key)}")
        model.add(penalty == sum(variables) - used)
        penalties.append(penalty)
        upper += len(variables)

    total = model.new_int_var(0, upper, name)
    model.add(total == sum(penalties)) if penalties else model.add(total == 0)
    return total
