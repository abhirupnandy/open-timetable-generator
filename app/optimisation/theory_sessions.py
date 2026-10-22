from __future__ import annotations

from collections import Counter

from ortools.sat.python import cp_model

from app.db.models.subject import SubjectType
from app.domain.calendar import Day
from app.domain.schedule import Timetable

MAX_THEORY_SESSIONS_PER_DAY = 2


def calculate_theory_sessions_penalty(timetable: Timetable) -> int:
    """
    Calculate the S11 theory-session penalty.

    For each faculty member and day, count LECTURE sessions.
    The first two lecture sessions on a day have no penalty.

    Penalty for each faculty/day:
        max(0, lecture_sessions - 2)

    LAB and TUTORIAL sessions do not count as theory sessions.
    """

    theory_sessions: Counter[tuple[int, Day]] = Counter()

    for placement in timetable.placements:
        if placement.session.subject_type != SubjectType.LECTURE:
            continue

        key = (
            placement.session.faculty_id,
            placement.day,
        )
        theory_sessions[key] += 1

    return sum(
        max(0, count - MAX_THEORY_SESSIONS_PER_DAY)
        for count in theory_sessions.values()
    )


def build_theory_sessions_objective(
    model: cp_model.CpModel,
    *,
    theory_session_variables: dict[
        tuple[int, int],
        list[cp_model.IntVar],
    ],
) -> cp_model.IntVar:
    """
    Build the S11 CP-SAT objective.

    Each dictionary key identifies:
        (faculty_id, day_index)

    The associated Boolean variables represent theory sessions
    that may be scheduled for that faculty member on that day.

    Penalty:
        max(0, number_of_theory_sessions - 2)
    """

    penalty_variables: list[cp_model.IntVar] = []

    for (faculty_id, day_index), variables in theory_session_variables.items():
        theory_count = model.new_int_var(
            0,
            len(variables),
            f"s11_theory_count_{faculty_id}_{day_index}",
        )

        if variables:
            model.add(theory_count == sum(variables))
        else:
            model.add(theory_count == 0)

        penalty = model.new_int_var(
            0,
            max(0, len(variables) - MAX_THEORY_SESSIONS_PER_DAY),
            f"s11_penalty_{faculty_id}_{day_index}",
        )

        model.add(
            penalty
            >= theory_count - MAX_THEORY_SESSIONS_PER_DAY
        )

        model.add(
            penalty
            >= 0
        )

        penalty_variables.append(penalty)

    objective = model.new_int_var(
        0,
        sum(
            max(0, len(variables) - MAX_THEORY_SESSIONS_PER_DAY)
            for variables in theory_session_variables.values()
        ),
        "s11_theory_sessions_penalty",
    )

    if penalty_variables:
        model.add(objective == sum(penalty_variables))
    else:
        model.add(objective == 0)

    return objective