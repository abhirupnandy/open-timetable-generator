from __future__ import annotations

from enum import StrEnum

from app.domain.conflicts import (
    academic_group_conflict,
    faculty_conflict,
)
from app.domain.placement import SessionPlacement


class HardConflictReason(StrEnum):
    FACULTY = "FACULTY"
    ACADEMIC_GROUP = "ACADEMIC_GROUP"


def hard_conflict_reasons(
    first: SessionPlacement,
    second: SessionPlacement,
    academic_group_parent_ids: dict[int, int | None] | None = None,
) -> tuple[HardConflictReason, ...]:
    """Return all supported hard-constraint violations between two placements."""

    reasons: list[HardConflictReason] = []

    if faculty_conflict(first, second):
        reasons.append(HardConflictReason.FACULTY)

    if academic_group_conflict(
        first,
        second,
        academic_group_parent_ids,
    ):
        reasons.append(HardConflictReason.ACADEMIC_GROUP)

    return tuple(reasons)


def has_hard_conflict(
    first: SessionPlacement,
    second: SessionPlacement,
    academic_group_parent_ids: dict[int, int | None] | None = None,
) -> bool:
    """Return whether two placements violate a supported hard constraint."""

    return bool(
        hard_conflict_reasons(
            first,
            second,
            academic_group_parent_ids,
        )
    )