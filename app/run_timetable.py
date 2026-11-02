from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

from app.core.timetable_config import TimetableConfigError, load_timetable_config
from app.db.session import SessionLocal
from app.domain.db_input import build_timetable_input_from_db
from app.domain.db_render_data import load_render_metadata
from app.domain.diagnostics import PreSolveError
from app.domain.problem import SchedulingProblem
from app.domain.render import render_timetable
from app.domain.timetable_view_builder import build_timetable_view_entries
from app.domain.validator import validate_timetable
from app.export.csv_export import export_timetable_csv, load_previous_placements
from app.export.excel_export import (
    export_day_workbook,
    export_faculty_workbook,
    export_grid_workbook,
    export_master_workbook,
)
from app.optimisation.score_report import (
    build_score_report,
    format_score_report,
    headline_metrics,
    score_report_payload,
    summary_sheet_rows,
    write_score_report,
)
from app.optimisation.solver import InfeasibleTimetableError, solve


def _show_solver_progress(stop_event: threading.Event) -> None:
    """Print periodic progress while CP-SAT is solving."""
    start_time = time.perf_counter()

    while not stop_event.wait(5):
        elapsed = time.perf_counter() - start_time
        print(
            f"[SOLVER] CP-SAT still running... {elapsed:.0f}s elapsed",
            flush=True,
        )


def _peak_memory_mb() -> float | None:
    try:
        import resource
    except ImportError:  # pragma: no cover - not available on Windows
        return None

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB, macOS reports bytes.
    return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a timetable with CP-SAT.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to the timetable TOML config (default: config/timetable.toml).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for CSV/Excel/JSON outputs (default: output).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    total_start = time.perf_counter()

    try:
        config = load_timetable_config(args.config)
    except TimetableConfigError as exc:
        print(exc, file=sys.stderr)
        return 2

    print("Configuration:", flush=True)
    for line in config.summary_lines():
        print(f"  {line}")
    print()

    print("[1/5] Loading timetable data from database...", flush=True)

    with SessionLocal() as db:
        (
            subject_names,
            group_metadata,
            faculty_names,
            room_names,
            course_metadata,
        ) = load_render_metadata(db)

        previous_placements = None
        stability = config.soft.stability_vs_previous

        if stability.enabled:
            previous_path = Path(stability.previous_timetable)
            if previous_path.exists():
                previous_placements = load_previous_placements(
                    previous_path,
                    {name: room_id for room_id, name in room_names.items()},
                )
                print(
                    f"[1/5] Loaded {len(previous_placements)} previous placements "
                    f"from {previous_path}",
                    flush=True,
                )
            else:
                print(
                    f"[1/5] stability_vs_previous: {previous_path} not found; ignoring.",
                    flush=True,
                )

        timetable_input = build_timetable_input_from_db(
            db,
            config,
            previous_placements=previous_placements,
        )

    group_names = {group_id: name for group_id, (_, name) in group_metadata.items()}

    print(
        f"[1/5] Loaded {len(timetable_input.sessions)} scheduling sessions "
        f"and {len(timetable_input.rooms or ())} rooms.",
        flush=True,
    )

    print("[2/5] Building scheduling problem...", flush=True)

    problem = SchedulingProblem(timetable_input=timetable_input)

    print("[3/5] Running CP-SAT solver...", flush=True)

    stop_event = threading.Event()
    progress_thread = threading.Thread(
        target=_show_solver_progress,
        args=(stop_event,),
        daemon=True,
    )
    progress_thread.start()

    try:
        result = solve(problem, config)
    except (PreSolveError, InfeasibleTimetableError) as exc:
        print(f"\n{exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        stop_event.set()
        progress_thread.join()

    for diagnostic in result.diagnostics:
        print(f"[3/5] {diagnostic}", flush=True)

    peak = _peak_memory_mb()
    print(
        f"[3/5] Solver finished: status={result.status}, "
        f"objective={result.objective_value}, bound={result.best_bound}, "
        f"build={result.build_time_seconds:.2f}s, solve={result.wall_time_seconds:.2f}s"
        + (f", peak memory={peak:.0f} MB" if peak is not None else ""),
        flush=True,
    )
    print(f"[3/5] Model: {result.model_stats}", flush=True)

    print("[4/5] Validating solver output...", flush=True)

    validation = validate_timetable(
        result.timetable,
        timetable_input.academic_group_parent_ids,
        timetable_input=timetable_input,
        config=config,
    )

    if validation.is_valid:
        print("[4/5] Hard constraints: PASS", flush=True)
    else:
        print(
            f"[4/5] Hard constraints: FAIL ({len(validation.conflicts)} conflicts, "
            f"{len(validation.violations)} violations)",
            flush=True,
        )

        for conflict in validation.conflicts:
            reasons = ", ".join(reason.value for reason in conflict.reasons)
            print(
                f"  {conflict.first_session_id} <-> {conflict.second_session_id}: {reasons}",
                flush=True,
            )

        for violation in validation.violations:
            print(f"  {violation.reason.value}: {violation.message}", flush=True)

        raise RuntimeError("Generated timetable violates hard constraints.")

    print(
        f"[4/5] Scheduled {len(result.timetable.placements)} "
        f"of {len(timetable_input.sessions)} sessions.",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Score report
    # ------------------------------------------------------------------

    rows = build_score_report(result, timetable_input, config)
    metrics = headline_metrics(result.timetable, timetable_input, config)
    payload = score_report_payload(rows, result, metrics)

    print()
    print(format_score_report(rows))
    print()
    print("Headline metrics:")
    for key, value in metrics.items():
        print(f"  {key:<30} {value}")
    print()

    if payload["mismatches"]:
        print(
            "WARNING: solver and independent calculator disagree for: "
            + ", ".join(payload["mismatches"]),
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
    # Exports
    # ------------------------------------------------------------------

    print("[5/5] Preparing timetable export data...", flush=True)

    with SessionLocal() as db:
        view_entries = build_timetable_view_entries(db, result.timetable)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    group_codes = {group_id: code for group_id, (code, _) in group_metadata.items()}
    group_parents = {
        group_codes[group_id]: group_codes.get(parent_id) if parent_id is not None else None
        for group_id, parent_id in (timetable_input.academic_group_parent_ids or {}).items()
        if group_id in group_codes
    }
    day_names = [day.value for day in timetable_input.days]

    exports = [
        ("score report", lambda: write_score_report(payload, output_dir / "score_report.json")),
        ("CSV", lambda: export_timetable_csv(view_entries, output_dir / "timetable_master.csv")),
        (
            "master workbook",
            lambda: export_master_workbook(
                view_entries,
                output_dir / "timetable_master.xlsx",
                summary_rows=summary_sheet_rows(payload),
            ),
        ),
        (
            "day-wise workbook",
            lambda: export_day_workbook(view_entries, output_dir / "timetable_by_day.xlsx"),
        ),
        (
            "faculty-wise workbook",
            lambda: export_faculty_workbook(view_entries, output_dir / "timetable_by_faculty.xlsx"),
        ),
    ]

    for by, filename in (
        ("group", "grid_by_group.xlsx"),
        ("faculty", "grid_by_faculty.xlsx"),
        ("room", "grid_by_room.xlsx"),
    ):
        exports.append(
            (
                f"{by} grid workbook",
                lambda by=by, filename=filename: export_grid_workbook(
                    view_entries,
                    output_dir / filename,
                    by=by,
                    days=day_names,
                    periods_per_day=timetable_input.periods_per_day,
                    group_parents=group_parents,
                ),
            )
        )

    for label, export in exports:
        path = export()
        print(f"[5/5] Exported {label} to {path}", flush=True)

    total_elapsed = time.perf_counter() - total_start

    print()
    print(f"Completed in {total_elapsed:.2f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
