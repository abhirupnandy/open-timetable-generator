from __future__ import annotations

from app.domain.placement import SessionPlacement
from app.domain.time_slots import valid_start_periods
from app.domain.timetable import TimetableInput


def candidate_placements(
    session_id: str,
    timetable_input: TimetableInput,
) -> tuple[SessionPlacement, ...]:
    """Generate all valid placements for one scheduling session."""

    session = next(
        session
        for session in timetable_input.sessions
        if session.id == session_id
    )

    start_periods = valid_start_periods(
        periods_per_day=timetable_input.periods_per_day,
        duration_periods=session.duration_periods,
    )

    placements = (
        SessionPlacement(
            session=session,
            day=day,
            start_period=start_period,
        )
        for day in timetable_input.days
        for start_period in start_periods
    )

    faculty_availability = (
        timetable_input.faculty_availability.get(session.faculty_id)
        if timetable_input.faculty_availability is not None
        else None
    )

    if faculty_availability is not None:
        placements = (
            placement
            for placement in placements
            if faculty_availability.is_available(
                day=placement.day,
                start_period=placement.start_period,
                duration_periods=session.duration_periods,
            )
        )

    return tuple(placements)