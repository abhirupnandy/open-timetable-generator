from __future__ import annotations

from dataclasses import dataclass

from app.domain.timetable import Day, SchedulingSession


@dataclass(frozen=True)
class SessionPlacement:
    """A concrete day/start-period placement for a scheduling session."""

    session: SchedulingSession
    day: Day
    start_period: int

    @property
    def end_period(self) -> int:
        """Return the final period occupied by the session."""
        return self.start_period + self.session.duration_periods - 1

    @property
    def occupied_periods(self) -> tuple[int, ...]:
        """Return all periods occupied by the session."""
        return tuple(
            range(
                self.start_period,
                self.end_period + 1,
            )
        )

def is_valid_placement(
    placement: SessionPlacement,
    *,
    days: tuple[Day, ...],
    periods_per_day: int,
) -> bool:
    """Return whether a placement fits within the timetable grid."""

    if not days:
        return False

    if periods_per_day <= 0:
        return False

    if placement.day not in days:
        return False

    if placement.start_period < 1:
        return False

    return placement.end_period <= periods_per_day

def placements_overlap(
    first: SessionPlacement,
    second: SessionPlacement,
) -> bool:
    """Return whether two placements occupy overlapping periods on the same day."""

    if first.day != second.day:
        return False

    return (
        first.start_period <= second.end_period
        and second.start_period <= first.end_period
    )