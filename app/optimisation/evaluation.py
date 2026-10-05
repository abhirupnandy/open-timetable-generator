from __future__ import annotations

from collections import defaultdict

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