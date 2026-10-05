from __future__ import annotations

import threading
import time

from app.db.session import SessionLocal
from app.domain.db_input import build_timetable_input_from_db
from app.domain.db_render_data import load_render_metadata
from app.domain.problem import SchedulingProblem
from app.domain.render import render_timetable
from app.domain.validator import validate_timetable
from app.optimisation.evaluation import calculate_student_group_gaps
from app.optimisation.solver import solve


def _show_solver_progress(stop_event: threading.Event) -> None:
    """Print periodic progress while CP-SAT is solving."""
    start_time = time.perf_counter()

    while not stop_event.wait(5):
        elapsed = time.perf_counter() - start_time
        print(
            f"[SOLVER] CP-SAT still running... {elapsed:.0f}s elapsed",
            flush=True,
        )


def main() -> None:
    total_start = time.perf_counter()

    print("[1/5] Loading timetable data from database...", flush=True)

    with SessionLocal() as db:
        timetable_input = build_timetable_input_from_db(db)
        (
            subject_names,
            group_metadata,
            faculty_names,
            room_names,
            course_metadata,
        ) = load_render_metadata(db)

    group_names = {
        group_id: name
        for group_id, (_, name) in group_metadata.items()
    }

    print(
        f"[1/5] Loaded {len(timetable_input.sessions)} scheduling sessions "
        f"and {len(timetable_input.rooms or ())} rooms.",
        flush=True,
    )

    print("[2/5] Building scheduling problem...", flush=True)
    problem = SchedulingProblem(timetable_input=timetable_input)
    print("[2/5] Scheduling problem ready.", flush=True)

    print("[3/5] Running CP-SAT solver...", flush=True)

    stop_event = threading.Event()
    progress_thread = threading.Thread(
        target=_show_solver_progress,
        args=(stop_event,),
        daemon=True,
    )

    solve_start = time.perf_counter()
    progress_thread.start()

    try:
        result = solve(problem)
    finally:
        stop_event.set()
        progress_thread.join()

    solve_elapsed = time.perf_counter() - solve_start

    print(
        f"[3/5] Solver finished in {solve_elapsed:.2f}s.",
        flush=True,
    )

    print("[4/5] Validating solver output...", flush=True)

    validation = validate_timetable(result.timetable)

    if validation.is_valid:
        print("[4/5] Hard constraints: PASS", flush=True)
        print("[4/5] Hard conflicts: 0", flush=True)
    else:
        print(
            f"[4/5] Hard constraints: FAIL "
            f"({len(validation.conflicts)} conflicts)",
            flush=True,
        )

        for conflict in validation.conflicts:
            reasons = ", ".join(
                reason.value
                for reason in conflict.reasons
            )
            print(
                f"  {conflict.first_session_id} <-> "
                f"{conflict.second_session_id}: {reasons}",
                flush=True,
            )

        raise RuntimeError(
            "Generated timetable violates hard constraints."
        )

    print(
        f"[4/5] Scheduled {len(result.timetable.placements)} "
        f"of {len(timetable_input.sessions)} sessions.",
        flush=True,
    )

    s1_gaps = calculate_student_group_gaps(
        result.timetable,
        periods_per_day=timetable_input.periods_per_day,
    )

    print(
        f"[4/5] Student-group gaps (S1): {s1_gaps}",
        flush=True,
    )

    print("[5/5] Rendering timetable...", flush=True)
    print()

    print(
        render_timetable(
            result.timetable,
            subject_names=subject_names,
            group_names=group_names,
            faculty_names=faculty_names,
            room_names=room_names,
        )
    )

    total_elapsed = time.perf_counter() - total_start
    print()
    print(f"Completed in {total_elapsed:.2f}s.")


if __name__ == "__main__":
    main()