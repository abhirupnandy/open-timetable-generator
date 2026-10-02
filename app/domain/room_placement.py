from __future__ import annotations

from app.domain.placement import SessionPlacement
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import SchedulingRoom


def is_room_available_for_placement(
    room: SchedulingRoom,
    placement: SessionPlacement,
    availability: ResourceAvailability | None,
) -> bool:
    """Return whether a room is available for a session placement."""

    if availability is None:
        return True

    return availability.is_available(
        day=placement.day,
        start_period=placement.start_period,
        duration_periods=placement.session.duration_periods,
    )