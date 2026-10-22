from __future__ import annotations

from collections import Counter

from app.domain.schedule import Timetable


def calculate_s4_penalty(timetable: Timetable) -> int:
    """
    Calculate the S4 subject-spreading penalty.

    For each:
        subject + academic group + day

    the first occurrence of the subject on that day has no penalty.
    Every additional occurrence adds one penalty.

    Therefore:

        penalty = max(0, number_of_occurrences - 1)

    The total S4 penalty is the sum across all subject/group/day
    combinations.

    Multi-period sessions count as one occurrence because a session
    represents one weekly meeting of a subject.
    """

    occurrences: Counter[tuple[int, int, object]] = Counter()

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