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


def _academic_group_ancestors(
    group_id: int,
    parent_group_ids: dict[int, int | None],
) -> set[int]:
    """Return the group and all of its ancestors."""

    ancestors: set[int] = set()
    current_group_id: int | None = group_id

    while current_group_id is not None:
        if current_group_id in ancestors:
            raise ValueError("Academic group hierarchy contains a cycle")

        ancestors.add(current_group_id)
        current_group_id = parent_group_ids.get(current_group_id)

    return ancestors


def academic_group_conflict(
    first: SessionPlacement,
    second: SessionPlacement,
    parent_group_ids: dict[int, int | None] | None = None,
) -> bool:
    """Return whether two overlapping sessions have overlapping students."""

    if not placements_overlap(first, second):
        return False

    first_group_id = first.session.academic_group_id
    second_group_id = second.session.academic_group_id

    if first_group_id == second_group_id:
        return True

    if parent_group_ids is None:
        return False

    first_ancestors = _academic_group_ancestors(
        first_group_id,
        parent_group_ids,
    )
    second_ancestors = _academic_group_ancestors(
        second_group_id,
        parent_group_ids,
    )

    return bool(first_ancestors.intersection(second_ancestors))