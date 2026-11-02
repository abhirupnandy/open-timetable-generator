from __future__ import annotations

from enum import StrEnum


class Day(StrEnum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"


# Fallback period start/end times (minutes from midnight), used only when a
# TimetableInput does not carry its own ``period_times``. The calendar used
# for real runs comes from ``config/timetable.toml``.
#
# P1: 08:20–09:20
# P2: 09:25–10:25
# P3: 10:30–11:30
# P4: 11:35–12:35
# P5: 13:45–14:45
# P6: 14:50–15:50
# P7: 15:55–16:55
# P8: 17:00–18:00
DEFAULT_PERIOD_TIMES: dict[int, tuple[int, int]] = {
    1: (8 * 60 + 20, 9 * 60 + 20),
    2: (9 * 60 + 25, 10 * 60 + 25),
    3: (10 * 60 + 30, 11 * 60 + 30),
    4: (11 * 60 + 35, 12 * 60 + 35),
    5: (13 * 60 + 45, 14 * 60 + 45),
    6: (14 * 60 + 50, 15 * 60 + 50),
    7: (15 * 60 + 55, 16 * 60 + 55),
    8: (17 * 60, 18 * 60),
}

# Backwards-compatible alias.
PERIOD_TIMES = DEFAULT_PERIOD_TIMES


def period_start_minutes(
    period: int,
    period_times: dict[int, tuple[int, int]] | None = None,
) -> int:
    """Return the timetable start time of a period in minutes from midnight."""

    try:
        return (period_times or DEFAULT_PERIOD_TIMES)[period][0]
    except KeyError as exc:
        raise ValueError(f"Invalid timetable period: {period}") from exc


def period_end_minutes(
    period: int,
    period_times: dict[int, tuple[int, int]] | None = None,
) -> int:
    """Return the timetable end time of a period in minutes from midnight."""

    try:
        return (period_times or DEFAULT_PERIOD_TIMES)[period][1]
    except KeyError as exc:
        raise ValueError(f"Invalid timetable period: {period}") from exc