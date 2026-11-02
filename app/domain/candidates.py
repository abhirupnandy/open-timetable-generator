from __future__ import annotations

from app.domain.placement import SessionPlacement
from app.domain.populations import GroupHierarchy
from app.domain.time_slots import valid_start_periods
from app.domain.timetable import SchedulingSession, TimetableInput


def crosses_lunch(placement: SessionPlacement, lunch_after_period: int | None) -> bool:
    """Return whether a placement occupies both sides of the lunch break."""

    if lunch_after_period is None:
        return False

    return (
        placement.start_period <= lunch_after_period
        and placement.end_period >= lunch_after_period + 1
    )


def _occupies(placement: SessionPlacement, day, period: int) -> bool:
    return placement.day == day and placement.start_period <= period <= placement.end_period


def _resolve_session(
    session: SchedulingSession | str,
    timetable_input: TimetableInput,
) -> SchedulingSession:
    if isinstance(session, SchedulingSession):
        return session

    for candidate in timetable_input.sessions:
        if candidate.id == session:
            return candidate

    raise KeyError(f"Unknown scheduling session: {session}")


def candidate_placements(
    session: SchedulingSession | str,
    timetable_input: TimetableInput,
    *,
    forbid_across_lunch: bool = False,
    apply_group_blocks: bool = True,
    apply_locks: bool = True,
    hierarchy: GroupHierarchy | None = None,
) -> tuple[SessionPlacement, ...]:
    """Generate all valid placements for one scheduling session.

    ``session`` may be the session object (preferred) or its id.

    Filters applied, in order: fits in the day, global blocked slots,
    group blocked slots (for any group sharing students with the session),
    the lunch rule (hard mode only), session locks and faculty availability.
    """

    session = _resolve_session(session, timetable_input)

    start_periods = valid_start_periods(
        periods_per_day=timetable_input.periods_per_day,
        duration_periods=session.duration_periods,
    )

    placements = [
        SessionPlacement(session=session, day=day, start_period=start_period)
        for day in timetable_input.days
        for start_period in start_periods
    ]

    if timetable_input.blocked_slots:
        placements = [
            placement
            for placement in placements
            if not any(
                _occupies(placement, slot.day, slot.period)
                for slot in timetable_input.blocked_slots
            )
        ]

    if apply_group_blocks and timetable_input.group_blocked_slots:
        if hierarchy is None:
            hierarchy = GroupHierarchy(timetable_input.academic_group_parent_ids)

        relevant_blocks = [
            block
            for block in timetable_input.group_blocked_slots
            if hierarchy.populations_overlap(block.academic_group_id, session.academic_group_id)
        ]

        if relevant_blocks:
            placements = [
                placement
                for placement in placements
                if not any(
                    _occupies(placement, block.day, block.period) for block in relevant_blocks
                )
            ]

    if forbid_across_lunch and not session.allow_across_lunch:
        placements = [
            placement
            for placement in placements
            if not crosses_lunch(placement, timetable_input.lunch_after_period)
        ]

    if apply_locks and timetable_input.session_locks:
        lock = next(
            (lock for lock in timetable_input.session_locks if lock.session_id == session.id),
            None,
        )

        if lock is not None:
            placements = [
                placement
                for placement in placements
                if placement.day == lock.day and placement.start_period == lock.start_period
            ]

    faculty_availability = (
        timetable_input.faculty_availability.get(session.faculty_id)
        if timetable_input.faculty_availability is not None
        else None
    )

    if faculty_availability is not None:
        placements = [
            placement
            for placement in placements
            if faculty_availability.is_available(
                day=placement.day,
                start_period=placement.start_period,
                duration_periods=session.duration_periods,
            )
        ]

    return tuple(placements)
