from __future__ import annotations

from app.domain.schedule import Timetable

MORNING_PERIODS = frozenset({1, 2, 3, 4})
AFTERNOON_PERIODS = frozenset({5, 6, 7, 8})
EVENING_PERIODS = frozenset({7, 8})


def calculate_s3_penalty(
    timetable: Timetable,
    *,
    faculty_time_preferences: dict[int, str],
) -> int:
    """
    Calculate the S3 faculty time-preference penalty.

    Preference rules:

    ANY:
        No penalty.

    MORNING:
        Periods 1-4 are preferred.
        Each occupied period in P5-P8 incurs one penalty.

    AFTERNOON:
        Periods 5-8 are preferred.
        Each occupied period in P1-P4 incurs one penalty.

    EVENING:
        Periods 7-8 are preferred.
        Each occupied period in P1-P6 incurs one penalty.

    Multi-period sessions are evaluated period-by-period.

    Faculty without an entry in faculty_time_preferences are treated
    as having no preference and therefore incur no penalty.
    """

    penalty = 0

    for placement in timetable.placements:
        faculty_id = placement.session.faculty_id
        preference = faculty_time_preferences.get(faculty_id, "ANY")

        if preference == "ANY":
            continue

        occupied_periods = placement.occupied_periods

        if preference == "MORNING":
            penalty += sum(
                period not in MORNING_PERIODS
                for period in occupied_periods
            )

        elif preference == "AFTERNOON":
            penalty += sum(
                period not in AFTERNOON_PERIODS
                for period in occupied_periods
            )

        elif preference == "EVENING":
            penalty += sum(
                period not in EVENING_PERIODS
                for period in occupied_periods
            )

        else:
            raise ValueError(
                f"Unknown faculty time preference: {preference!r}"
            )

    return penalty