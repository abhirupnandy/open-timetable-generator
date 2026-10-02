from __future__ import annotations

from app.domain.candidates import candidate_placements
from app.domain.placement import SessionPlacement
from app.domain.problem import SchedulingProblem


class EmptyCandidateDomainError(ValueError):
    """Raised when a scheduling session has no valid candidate placement."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            f"Scheduling session has no valid candidate placements: {session_id}"
        )
        self.session_id = session_id


def build_candidate_domains(
    problem: SchedulingProblem,
) -> dict[str, tuple[SessionPlacement, ...]]:
    """Build the candidate placement domain for every scheduling session."""

    domains: dict[str, tuple[SessionPlacement, ...]] = {}

    for session in problem.sessions:
        placements = candidate_placements(
            session.id,
            problem.timetable_input,
        )

        if not placements:
            raise EmptyCandidateDomainError(session.id)

        domains[session.id] = placements

    return domains