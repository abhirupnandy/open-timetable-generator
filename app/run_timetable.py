from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace

from app.db.session import SessionLocal
from app.domain.db_input import build_timetable_input_from_db
from app.domain.db_render_data import load_render_metadata
from app.domain.problem import SchedulingProblem
from app.domain.render import render_timetable
from app.domain.timetable_view_builder import build_timetable_view_entries
from app.domain.validator import validate_timetable
from app.export.csv_export import export_timetable_csv
from app.export.excel_export import (
    export_day_workbook,
    export_faculty_workbook,
    export_master_workbook,
)
from app.optimisation.evaluation import calculate_student_group_gaps
from app.optimisation.faculty_time_preferences import (
    calculate_s3_penalty,
)
from app.optimisation.faculty_workload import calculate_s2_penalty
from app.optimisation.solver import solve
from app.optimisation.student_free_periods import (
    calculate_student_free_period_penalty,
)
from app.optimisation.theory_sessions import (
    calculate_theory_sessions_penalty,
)


def _show_solver_progress(stop_event: threading.Event) -> None:
    """Print periodic progress while CP-SAT is solving."""
    start_time = time.perf_counter()

    while not stop_event.wait(5):
        elapsed = time.perf_counter() - start_time
        print(
            f"[SOLVER] CP-SAT still running... {elapsed:.0f}s elapsed",
            flush=True,
        )


def _calculate_faculty_workloads(
    timetable,
) -> tuple[SimpleNamespace, ...]:
    """
    Build faculty workload records from the generated timetable.

    Each timetable period represents one teaching hour. Multi-period
    sessions therefore contribute their full duration.
    """
    teaching_hours: dict[int, int] = {}

    for placement in timetable.placements:
        faculty_id = placement.session.faculty_id
        duration = placement.session.duration_periods

        teaching_hours[faculty_id] = (
            teaching_hours.get(faculty_id, 0)
            + duration
        )

    return tuple(
        SimpleNamespace(
            faculty_id=faculty_id,
            designation=designation,
            teaching_hours=teaching_hours.get(faculty_id, 0),
        )
        for faculty_id, designation in timetable.faculty_designations.items()
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

    problem = SchedulingProblem(
        timetable_input=timetable_input,
    )

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

    # ------------------------------------------------------------------
    # S1: Student-group gaps
    # ------------------------------------------------------------------

    s1_gaps = calculate_student_group_gaps(
        result.timetable,
        periods_per_day=timetable_input.periods_per_day,
    )

    print(
        f"[4/5] Student-group gaps (S1): {s1_gaps}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # S14: Minimum two free timetable periods per student group/day
    #
    # Lunch is outside the timetable period model and therefore
    # is not counted as a free period.
    # ------------------------------------------------------------------

    s14_penalty = calculate_student_free_period_penalty(
        result.timetable,
        periods_per_day=timetable_input.periods_per_day,
    )

    print(
        f"[4/5] Minimum free-period penalty (S14): {s14_penalty}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # S2: Faculty workload balance
    #
    # Faculty teaching hours are calculated from the generated
    # timetable. Utilisation is normalised using the faculty
    # designation capacity.
    # ------------------------------------------------------------------

    faculty_workloads = []

    for faculty_id, designation in (
        timetable_input.faculty_designations or {}
    ).items():
        teaching_hours = sum(
            placement.session.duration_periods
            for placement in result.timetable.placements
            if placement.session.faculty_id == faculty_id
        )

        faculty_workloads.append(
            type(
                "FacultyWorkload",
                (),
                {
                    "faculty_id": faculty_id,
                    "designation": designation,
                    "teaching_hours": teaching_hours,
                },
            )()
        )

    s2_penalty = calculate_s2_penalty(
        faculty_workloads
    )

    print(
        f"[4/5] Faculty workload balance penalty (S2): {s2_penalty}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # S11: Maximum two theory/lecture sessions per faculty per day
    #
    # Only LECTURE sessions are counted.
    # LAB and TUTORIAL sessions do not contribute to S11.
    #
    # The first two lecture sessions for a faculty member on a day
    # have zero penalty. Every additional lecture session contributes
    # one penalty point.
    # ------------------------------------------------------------------

    s11_penalty = calculate_theory_sessions_penalty(
        result.timetable
    )

    print(
        f"[4/5] Theory-session penalty (S11): {s11_penalty}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # S3: Faculty time preferences
    #
    # Sessions scheduled outside a faculty member's preferred
    # time range contribute one penalty per occupied period.
    # ------------------------------------------------------------------

    s3_penalty = calculate_s3_penalty(
        result.timetable,
        faculty_time_preferences=(
            timetable_input.faculty_time_preferences or {}
        ),
    )

    print(
        f"[4/5] Faculty time-preference penalty (S3): {s3_penalty}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Export preparation
    # ------------------------------------------------------------------

    print(
        "[5/5] Preparing timetable export data...",
        flush=True,
    )

    with SessionLocal() as db:
        view_entries = build_timetable_view_entries(
            db,
            result.timetable,
        )

    output_dir = Path("output")
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    print(
        "[5/5] Exporting CSV...",
        flush=True,
    )

    csv_path = export_timetable_csv(
        view_entries,
        output_dir / "timetable_master.csv",
    )

    print(
        f"[5/5] CSV exported to {csv_path}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Master Excel workbook
    # ------------------------------------------------------------------

    print(
        "[5/5] Exporting master Excel workbook...",
        flush=True,
    )

    master_excel_path = export_master_workbook(
        view_entries,
        output_dir / "timetable_master.xlsx",
    )

    print(
        f"[5/5] Master Excel exported to {master_excel_path}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Day-wise Excel workbook
    # ------------------------------------------------------------------

    print(
        "[5/5] Exporting day-wise Excel workbook...",
        flush=True,
    )

    day_excel_path = export_day_workbook(
        view_entries,
        output_dir / "timetable_by_day.xlsx",
    )

    print(
        f"[5/5] Day-wise Excel exported to {day_excel_path}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Faculty-wise Excel workbook
    # ------------------------------------------------------------------

    print(
        "[5/5] Exporting faculty-wise Excel workbook...",
        flush=True,
    )

    faculty_excel_path = export_faculty_workbook(
        view_entries,
        output_dir / "timetable_by_faculty.xlsx",
    )

    print(
        f"[5/5] Faculty-wise Excel exported to {faculty_excel_path}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Final timing
    # ------------------------------------------------------------------

    total_elapsed = time.perf_counter() - total_start

    print()
    print(
        f"Completed in {total_elapsed:.2f}s."
    )


if __name__ == "__main__":
    main()