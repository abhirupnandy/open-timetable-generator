from __future__ import annotations


def valid_start_periods(
    *,
    periods_per_day: int,
    duration_periods: int,
) -> tuple[int, ...]:
    """Return period numbers at which a session can start."""

    if periods_per_day <= 0:
        raise ValueError("periods_per_day must be greater than 0")

    if duration_periods <= 0:
        raise ValueError("duration_periods must be greater than 0")

    if duration_periods > periods_per_day:
        return ()

    last_start = periods_per_day - duration_periods + 1

    return tuple(range(1, last_start + 1))