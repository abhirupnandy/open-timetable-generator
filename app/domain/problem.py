from __future__ import annotations

from dataclasses import dataclass

from app.domain.schedule import Timetable
from app.domain.timetable import TimetableInput


@dataclass(frozen=True)
class SchedulingProblem:
    """Inputs required to construct a timetable."""

    timetable_input: TimetableInput

    @property
    def sessions(self):
        return self.timetable_input.sessions


@dataclass(frozen=True)
class SchedulingSolution:
    """A candidate solution produced by a scheduling process."""

    timetable: Timetable