from __future__ import annotations

from dataclasses import dataclass

from app.domain.calendar import Day


@dataclass(frozen=True)
class AvailabilityWindow:
    """A contiguous range of available periods on a specific day."""

    day: Day
    start_period: int
    end_period: int

    def __post_init__(self) -> None:
        if self.start_period < 1:
            raise ValueError("start_period must be greater than 0")

        if self.end_period < self.start_period:
            raise ValueError("end_period must be greater than or equal to start_period")

    def contains(self, *, day: Day, start_period: int, duration_periods: int) -> bool:
        """Return whether a session fits completely inside this availability window."""

        if day != self.day:
            return False

        if start_period < 1 or duration_periods <= 0:
            return False

        end_period = start_period + duration_periods - 1

        return (
            start_period >= self.start_period
            and end_period <= self.end_period
        )