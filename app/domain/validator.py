from __future__ import annotations

from dataclasses import dataclass

from app.domain.hard_constraints import (
    HardConflictReason,
    hard_conflict_reasons,
)
from app.domain.schedule import Timetable


@dataclass(frozen=True)
class HardConflict:
    """A pair of sessions that violate one or more hard constraints."""

    first_session_id: str
    second_session_id: str
    reasons: tuple[HardConflictReason, ...]


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating a candidate timetable."""

    conflicts: tuple[HardConflict, ...]

    @property
    def is_valid(self) -> bool:
        return not self.conflicts


def validate_timetable(
    timetable: Timetable,
) -> ValidationResult:
    """Validate all placements in a candidate timetable."""

    conflicts: list[HardConflict] = []

    for index, first in enumerate(timetable.placements):
        for second in timetable.placements[index + 1 :]:
            reasons = hard_conflict_reasons(first, second)

            if reasons:
                conflicts.append(
                    HardConflict(
                        first_session_id=first.session.id,
                        second_session_id=second.session.id,
                        reasons=reasons,
                    )
                )

    return ValidationResult(conflicts=tuple(conflicts))