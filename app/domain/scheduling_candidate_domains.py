from __future__ import annotations

from app.domain.candidate_domains import EmptyCandidateDomainError
from app.domain.candidates import candidate_placements
from app.domain.problem import SchedulingProblem
from app.domain.room_candidate_domains import EmptyRoomCandidateDomainError
from app.domain.scheduling_candidate import SchedulingCandidate
from app.domain.scheduling_candidates import build_scheduling_candidates


def build_scheduling_candidate_domains(
    problem: SchedulingProblem,
) -> dict[str, tuple[SchedulingCandidate, ...]]:
    """Build the combined placement-and-room candidate domain for every session."""

    domains: dict[str, tuple[SchedulingCandidate, ...]] = {}

    rooms = problem.timetable_input.rooms or ()

    for session in problem.sessions:
        placements = candidate_placements(
            session.id,
            problem.timetable_input,
        )

        if not placements:
            raise EmptyCandidateDomainError(session.id)

        candidates: list[SchedulingCandidate] = []

        for placement in placements:
            try:
                placement_candidates = build_scheduling_candidates(
                    placement,
                    rooms,
                    problem.timetable_input,
                )
            except EmptyRoomCandidateDomainError:
                continue

            candidates.extend(placement_candidates)

        if not candidates:
            raise EmptyCandidateDomainError(session.id)

        domains[session.id] = tuple(candidates)

    return domains