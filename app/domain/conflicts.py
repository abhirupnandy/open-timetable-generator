from __future__ import annotations

from app.domain.placement import SessionPlacement, placements_overlap


def faculty_conflict(
    first: SessionPlacement,
    second: SessionPlacement,
) -> bool:
    """Return whether two overlapping sessions use the same faculty member."""

    return (
        first.session.faculty_id == second.session.faculty_id
        and placements_overlap(first, second)
    )


def academic_group_conflict(
    first: SessionPlacement,
    second: SessionPlacement,
) -> bool:
    """Return whether two overlapping sessions use the same academic group."""

    return (
        first.session.academic_group_id == second.session.academic_group_id
        and placements_overlap(first, second)
    )