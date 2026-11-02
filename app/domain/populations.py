"""Student-population helpers based on the academic-group hierarchy.

A *leaf group* is an academic group with no child groups. Each leaf
represents a set of students that is never split further. A session for
group ``G`` is attended by every leaf that is ``G`` or a descendant of
``G``. Two sessions share students exactly when their leaf sets intersect,
which means:

* a parent group conflicts with each of its batches;
* sibling batches do not conflict and can run in parallel.
"""

from __future__ import annotations

from collections.abc import Iterable


class GroupHierarchy:
    """Precomputed ancestor / leaf information for academic groups."""

    def __init__(
        self,
        parent_ids: dict[int, int | None] | None,
        group_ids: Iterable[int] = (),
    ) -> None:
        self._parent_ids: dict[int, int | None] = dict(parent_ids or {})

        for group_id in group_ids:
            self._parent_ids.setdefault(group_id, None)

        self._children: dict[int, list[int]] = {group_id: [] for group_id in self._parent_ids}

        for group_id, parent_id in self._parent_ids.items():
            if parent_id is not None:
                self._children.setdefault(parent_id, []).append(group_id)
                self._parent_ids.setdefault(parent_id, None)

        self._ancestors: dict[int, frozenset[int]] = {}
        self._leaves: dict[int, tuple[int, ...]] = {}

    # -- basic relations ----------------------------------------------------

    @property
    def group_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self._parent_ids))

    def parent(self, group_id: int) -> int | None:
        return self._parent_ids.get(group_id)

    def children(self, group_id: int) -> tuple[int, ...]:
        return tuple(sorted(self._children.get(group_id, ())))

    def ancestors_or_self(self, group_id: int) -> frozenset[int]:
        cached = self._ancestors.get(group_id)

        if cached is not None:
            return cached

        seen: list[int] = []
        current: int | None = group_id

        while current is not None:
            if current in seen:
                raise ValueError("Academic group hierarchy contains a cycle")
            seen.append(current)
            current = self._parent_ids.get(current)

        result = frozenset(seen)
        self._ancestors[group_id] = result
        return result

    def leaves_of(self, group_id: int) -> tuple[int, ...]:
        """Return the leaf groups that are ``group_id`` or its descendants."""

        cached = self._leaves.get(group_id)

        if cached is not None:
            return cached

        leaves: list[int] = []
        stack = [group_id]
        visited: set[int] = set()

        while stack:
            current = stack.pop()

            if current in visited:
                raise ValueError("Academic group hierarchy contains a cycle")
            visited.add(current)

            children = self._children.get(current, ())

            if children:
                stack.extend(children)
            else:
                leaves.append(current)

        result = tuple(sorted(leaves))
        self._leaves[group_id] = result
        return result

    def all_leaves(self) -> tuple[int, ...]:
        return tuple(
            sorted(group_id for group_id in self._parent_ids if not self._children.get(group_id))
        )

    def populations_overlap(self, first_group_id: int, second_group_id: int) -> bool:
        """Return whether two groups share any students."""

        if first_group_id == second_group_id:
            return True

        return first_group_id in self.ancestors_or_self(
            second_group_id
        ) or second_group_id in self.ancestors_or_self(first_group_id)


def populations_overlap(
    first_group_id: int,
    second_group_id: int,
    parent_ids: dict[int, int | None] | None,
) -> bool:
    """Convenience wrapper around :meth:`GroupHierarchy.populations_overlap`."""

    if first_group_id == second_group_id:
        return True

    if not parent_ids:
        return False

    return GroupHierarchy(parent_ids).populations_overlap(first_group_id, second_group_id)
