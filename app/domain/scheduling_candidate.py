from __future__ import annotations

from dataclasses import dataclass

from app.domain.placement import SessionPlacement
from app.domain.room import SchedulingRoom


@dataclass(frozen=True)
class SchedulingCandidate:
    """A concrete session placement with an optional physical room."""

    placement: SessionPlacement
    room: SchedulingRoom | None