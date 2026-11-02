from __future__ import annotations

from app.core.timetable_config import ConstraintMode, TimetableConfig
from app.domain.candidate_domains import EmptyCandidateDomainError
from app.domain.candidates import candidate_placements
from app.domain.diagnostics import Diagnostic, explain_no_placement, explain_no_room
from app.domain.populations import GroupHierarchy
from app.domain.problem import SchedulingProblem
from app.domain.room_candidates import candidate_rooms
from app.domain.room_placement import is_room_available_for_placement
from app.domain.scheduling_candidate import SchedulingCandidate


class EmptyDomainsError(EmptyCandidateDomainError):
    """One or more sessions have an empty candidate domain.

    ``session_id`` / ``reason`` describe the first offending session;
    ``diagnostics`` lists every offending session with its explanation.
    """

    def __init__(self, diagnostics: list[Diagnostic], session_id: str, reason: str) -> None:
        super().__init__(session_id, reason)
        self.diagnostics = diagnostics
        if len(diagnostics) > 1:
            details = "\n".join(f"  {item}" for item in diagnostics)
            self.args = (f"{self.args[0]}\nAll sessions without candidates:\n{details}",)


def build_scheduling_candidate_domains(
    problem: SchedulingProblem,
    config: TimetableConfig | None = None,
    *,
    hierarchy: GroupHierarchy | None = None,
) -> dict[str, tuple[SchedulingCandidate, ...]]:
    """Build the combined placement-and-room candidate domain for every session.

    Raises :class:`EmptyCandidateDomainError` (an :class:`EmptyDomainsError`)
    with an explanation when any session has no candidate.
    """

    config = config or TimetableConfig()
    timetable_input = problem.timetable_input

    if hierarchy is None:
        hierarchy = GroupHierarchy(
            timetable_input.academic_group_parent_ids,
            (session.academic_group_id for session in timetable_input.sessions),
        )

    forbid_across_lunch = config.constraints.no_session_across_lunch.mode == ConstraintMode.HARD
    apply_locks = config.hard.locked_sessions.enabled
    room_locks = (
        {
            lock.session_id: lock.room_id
            for lock in timetable_input.session_locks
            if lock.room_id is not None
        }
        if apply_locks
        else {}
    )

    rooms = timetable_input.rooms or ()
    room_availability = timetable_input.room_availability or {}

    domains: dict[str, tuple[SchedulingCandidate, ...]] = {}
    problems: list[tuple[str, str]] = []

    for session in problem.sessions:
        placements = candidate_placements(
            session,
            timetable_input,
            forbid_across_lunch=forbid_across_lunch,
            apply_group_blocks=config.hard.group_blocked_slots.enabled,
            apply_locks=apply_locks,
            hierarchy=hierarchy,
        )

        if not placements:
            problems.append(
                (session.id, explain_no_placement(session, timetable_input, config, hierarchy))
            )
            continue

        if session.mode == "ONLINE":
            domains[session.id] = tuple(
                SchedulingCandidate(placement=placement, room=None) for placement in placements
            )
            continue

        suitable_rooms = candidate_rooms(session, rooms, timetable_input)

        locked_room = room_locks.get(session.id)

        if locked_room is not None:
            suitable_rooms = tuple(room for room in suitable_rooms if room.id == locked_room)

        candidates: list[SchedulingCandidate] = []

        for placement in placements:
            if session.mode == "EITHER" and locked_room is None:
                candidates.append(SchedulingCandidate(placement=placement, room=None))

            candidates.extend(
                SchedulingCandidate(placement=placement, room=room)
                for room in suitable_rooms
                if is_room_available_for_placement(
                    room,
                    placement,
                    room_availability.get(room.id),
                )
            )

        if not candidates:
            reason = explain_no_room(session, timetable_input)
            if locked_room is not None:
                reason = f"locked room {locked_room} is unsuitable or unavailable ({reason})"
            problems.append((session.id, reason))
            continue

        domains[session.id] = tuple(candidates)

    if problems:
        diagnostics = [
            Diagnostic("error", "EMPTY_DOMAIN", f"{session_id}: {reason}")
            for session_id, reason in problems
        ]
        raise EmptyDomainsError(diagnostics, *problems[0])

    return domains
