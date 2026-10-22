from __future__ import annotations

from collections import Counter, defaultdict

from app.domain.calendar import Day
from app.domain.schedule import Timetable


def calculate_student_group_gaps(
    timetable: Timetable,
    *,
    periods_per_day: int,
) -> int:
    """Calculate the number of unoccupied periods inside each group's daily span."""
    if periods_per_day <= 0:
        raise ValueError("periods_per_day must be positive")

    occupied_periods: dict[tuple[int, Day], set[int]] = defaultdict(set)

    for placement in timetable.placements:
        group_id = placement.session.academic_group_id

        for period in placement.occupied_periods:
            occupied_periods[(group_id, placement.day)].add(period)

    total_gaps = 0

    for periods in occupied_periods.values():
        if len(periods) < 2:
            continue

        first_period = min(periods)
        last_period = max(periods)

        total_gaps += sum(
            1
            for period in range(first_period, last_period + 1)
            if period not in periods
        )

    return total_gaps


def calculate_subject_spreading_penalty(
    timetable: Timetable,
) -> int:
    """
    Calculate the S4 subject-spreading penalty.

    For each subject + academic group + day:

        penalty = max(0, number_of_sessions - 1)

    Therefore:

        1 session on a day -> 0
        2 sessions on a day -> 1
        3 sessions on a day -> 2

    The total penalty is summed across all
    subject/group/day combinations.

    A multi-period session counts as one occurrence because
    it represents one scheduled meeting of the subject.
    """

    occurrences: Counter[tuple[int, int, Day]] = Counter()

    for placement in timetable.placements:
        key = (
            placement.session.subject_id,
            placement.session.academic_group_id,
            placement.day,
        )
        occurrences[key] += 1

    return sum(
        max(0, count - 1)
        for count in occurrences.values()
    )