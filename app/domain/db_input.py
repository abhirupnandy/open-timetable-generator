from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timetable_config import TimetableConfig, load_timetable_config
from app.db.models import (
    AcademicGroup,
    Faculty,
    GroupBlockedSlot,
    ResourceType,
    Room,
    SessionLock,
    TeachingAssignment,
    Unavailability,
)
from app.domain.availability import AvailabilityWindow
from app.domain.input_builder import build_timetable_input
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import SchedulingRoom
from app.domain.timetable import Day, PreviousPlacement, TimetableInput
from app.domain.timetable import GroupBlockedSlot as DomainGroupBlockedSlot
from app.domain.timetable import SessionLock as DomainSessionLock


def unavailability_to_availability(
    records: list[tuple[int, Day, int, int]],
    *,
    days: tuple[Day, ...],
    periods_per_day: int,
) -> dict[int, ResourceAvailability]:
    """Convert unavailability ranges into availability windows.

    ``records`` holds ``(resource_id, day, start_period, end_period)``.
    For each resource with at least one record, every day is split into
    the maximal runs of periods that are not unavailable. Resources without
    records are absent from the result (fully available).
    """

    blocked: dict[int, set[tuple[Day, int]]] = defaultdict(set)

    for resource_id, day, start_period, end_period in records:
        for period in range(max(1, start_period), min(end_period, periods_per_day) + 1):
            blocked[resource_id].add((day, period))

    result: dict[int, ResourceAvailability] = {}

    for resource_id in {record[0] for record in records}:
        windows: list[AvailabilityWindow] = []

        for day in days:
            run_start: int | None = None

            for period in range(1, periods_per_day + 2):
                free = period <= periods_per_day and (day, period) not in blocked[resource_id]

                if free and run_start is None:
                    run_start = period
                elif not free and run_start is not None:
                    windows.append(
                        AvailabilityWindow(day=day, start_period=run_start, end_period=period - 1)
                    )
                    run_start = None

        result[resource_id] = ResourceAvailability(resource_id=resource_id, windows=tuple(windows))

    return result


def build_timetable_input_from_db(
    db: Session,
    config: TimetableConfig | None = None,
    *,
    previous_placements: dict[str, PreviousPlacement] | None = None,
) -> TimetableInput:
    config = config or load_timetable_config()
    calendar = config.calendar
    days = tuple(Day(day) for day in calendar.days)
    periods_per_day = calendar.periods_per_day

    teaching_assignments = tuple(
        db.scalars(select(TeachingAssignment).where(TeachingAssignment.is_active.is_(True))).all()
    )

    groups = tuple(db.scalars(select(AcademicGroup).where(AcademicGroup.is_active.is_(True))).all())

    faculty = tuple(db.scalars(select(Faculty).where(Faculty.is_active.is_(True))).all())

    rooms = tuple(db.scalars(select(Room).where(Room.is_active.is_(True))).all())

    unavailability = tuple(db.scalars(select(Unavailability)).all())

    faculty_records = [
        (item.resource_id, Day(item.day.value), item.start_period, item.end_period)
        for item in unavailability
        if item.resource_type == ResourceType.FACULTY
    ]
    room_records = [
        (item.resource_id, Day(item.day.value), item.start_period, item.end_period)
        for item in unavailability
        if item.resource_type == ResourceType.ROOM
    ]

    group_blocked_slots = tuple(
        DomainGroupBlockedSlot(
            academic_group_id=item.academic_group_id,
            day=Day(item.day.value),
            period=item.period,
            label=item.label or "",
        )
        for item in db.scalars(select(GroupBlockedSlot)).all()
    )

    session_locks = tuple(
        DomainSessionLock(
            session_id=f"assignment:{item.teaching_assignment_id}:session:{item.session_number}",
            day=Day(item.day.value),
            start_period=item.start_period,
            room_id=item.room_id,
        )
        for item in db.scalars(select(SessionLock)).all()
    )

    scheduling_rooms = tuple(
        SchedulingRoom(
            id=room.id,
            room_type=room.room_type,
            capacity=room.capacity,
            is_shared=room.is_shared,
        )
        for room in rooms
    )

    return build_timetable_input(
        teaching_assignments,
        days=days,
        periods_per_day=periods_per_day,
        calendar=calendar,
        academic_group_capacities={
            group.id: group.capacity for group in groups if group.capacity is not None
        },
        academic_group_parent_ids={group.id: group.parent_group_id for group in groups},
        faculty_designations={member.id: member.designation.value for member in faculty},
        faculty_time_preferences={member.id: member.time_preference.value for member in faculty},
        faculty_availability=(
            unavailability_to_availability(
                faculty_records, days=days, periods_per_day=periods_per_day
            )
            or None
        ),
        room_availability=(
            unavailability_to_availability(room_records, days=days, periods_per_day=periods_per_day)
            or None
        ),
        rooms=scheduling_rooms,
        group_blocked_slots=group_blocked_slots,
        session_locks=session_locks,
        faculty_preferred_day_off={
            member.id: Day(member.preferred_day_off.value)
            for member in faculty
            if member.preferred_day_off is not None
        }
        or None,
        previous_placements=previous_placements,
    )
