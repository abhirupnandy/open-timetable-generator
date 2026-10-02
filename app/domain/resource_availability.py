from __future__ import annotations

from dataclasses import dataclass

from app.domain.availability import AvailabilityWindow


@dataclass(frozen=True)
class ResourceAvailability:
    """Availability windows associated with a scheduling resource."""

    resource_id: int
    windows: tuple[AvailabilityWindow, ...]

    def is_available(
        self,
        *,
        day,
        start_period: int,
        duration_periods: int,
    ) -> bool:
        """Return whether the resource is available for the requested session."""

        return any(
            window.contains(
                day=day,
                start_period=start_period,
                duration_periods=duration_periods,
            )
            for window in self.windows
        )