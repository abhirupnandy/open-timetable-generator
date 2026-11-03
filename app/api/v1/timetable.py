"""Timetable generation endpoints.

A run is recorded in the ``timetable_runs`` table as soon as it is
requested, then executed in a background thread (CP-SAT can take minutes).
Each stage appends to the run's log. Failures are stored with a short
summary (why it failed) and full detail (diagnostics or traceback), so
past failures stay visible after a restart. Exports go to
``<output_dir>/runs/<id>/``.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import traceback
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1._common import get_config_store, get_timetable_config
from app.core.config import settings
from app.core.timetable_config import ConfigStore, TimetableConfig
from app.db.models import TimetableRun
from app.db.session import get_session_factory
from app.domain.db_input import build_timetable_input_from_db
from app.domain.db_render_data import load_render_metadata
from app.domain.diagnostics import PreSolveError
from app.domain.problem import SchedulingProblem
from app.domain.scheduling_candidate_domains import EmptyDomainsError
from app.domain.timetable import TimetableInput
from app.domain.timetable_view_builder import view_entries_from_metadata
from app.domain.validator import validate_timetable
from app.export.csv_export import export_timetable_csv
from app.export.excel_export import (
    export_day_workbook,
    export_faculty_workbook,
    export_grid_workbook,
    export_master_workbook,
)
from app.optimisation.score_report import (
    build_score_report,
    headline_metrics,
    score_report_payload,
    summary_sheet_rows,
    write_score_report,
)
from app.optimisation.solver import InfeasibleTimetableError, SolverResult, solve

logger = logging.getLogger("timetable.runs")

router = APIRouter(prefix="/timetable", tags=["Timetable"])

EXPORT_FILES = {
    "timetable_master.csv": "Master CSV",
    "timetable_master.xlsx": "Master workbook (with Summary)",
    "timetable_by_day.xlsx": "By day",
    "timetable_by_faculty.xlsx": "By faculty",
    "grid_by_group.xlsx": "Grid by group",
    "grid_by_faculty.xlsx": "Grid by faculty",
    "grid_by_room.xlsx": "Grid by room",
    "score_report.json": "Score report (JSON)",
}


class RunRequest(BaseModel):
    max_time_seconds: float | None = Field(default=None, gt=0, le=3600)


class RunFailure(Exception):
    """A run failed for a reason the user can act on."""

    def __init__(self, summary: str, detail: str = "") -> None:
        super().__init__(summary)
        self.summary = summary
        self.detail = detail


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _elapsed(run: TimetableRun) -> float:
    if run.status == "running":
        started = run.started_at if run.started_at.tzinfo else run.started_at.replace(tzinfo=UTC)
        return (datetime.now(UTC) - started).total_seconds()
    return run.elapsed_seconds


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()


def run_summary(run: TimetableRun) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "stage": run.stage,
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "elapsed_seconds": round(_elapsed(run), 2),
        "max_time_seconds": run.max_time_seconds,
        "session_count": run.session_count,
        "solver_status": run.solver_status,
        "total_weighted_penalty": run.total_weighted_penalty,
        "error": run.error_summary,
    }


def run_detail(run: TimetableRun) -> dict:
    files = json.loads(run.files_json or "[]")
    return {
        **run_summary(run),
        "error_detail": run.error_detail,
        "log": run.log,
        "files": [{"name": name, "label": EXPORT_FILES.get(name, name)} for name in files],
        "result": json.loads(run.result_json) if run.result_json else None,
    }


# ---------------------------------------------------------------------------
# Run manager
# ---------------------------------------------------------------------------


class RunManager:
    """Starts runs in background threads and records them in the database."""

    def __init__(self, session_factory: sessionmaker, output_dir: Path) -> None:
        self.session_factory = session_factory
        self.output_dir = Path(output_dir)
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self._recover_interrupted_runs()

    def _recover_interrupted_runs(self) -> None:
        try:
            with self.session_factory() as db:
                stale = db.scalars(
                    select(TimetableRun).where(TimetableRun.status == "running")
                ).all()
                for run in stale:
                    run.status = "failed"
                    run.error_summary = "The server stopped while this run was in progress."
                    run.error_detail = (
                        "The run was interrupted (server restart or crash) "
                        f"during stage '{run.stage}'. Start a new run."
                    )
                    run.finished_at = datetime.now(UTC)
                    run.log = (run.log or "") + f"{_stamp()} Interrupted by server restart\n"
                db.commit()
        except Exception:  # noqa: BLE001 - table may not exist before migrations
            logger.warning("Could not check for interrupted runs", exc_info=True)

    def files_dir(self, run_id: str) -> Path:
        return self.output_dir / "runs" / run_id

    def start(self, config: TimetableConfig) -> TimetableRun:
        with self._lock:
            with self.session_factory() as db:
                active = db.scalar(
                    select(TimetableRun.id).where(TimetableRun.status == "running").limit(1)
                )
                if active is not None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Run {active} is still in progress; wait for it to finish",
                    )
                run = TimetableRun(
                    id=uuid.uuid4().hex[:12],
                    status="running",
                    stage="queued",
                    started_at=datetime.now(UTC),
                    max_time_seconds=config.solver.max_time_seconds,
                    elapsed_seconds=0.0,
                    session_count=0,
                    log=(
                        f"{_stamp()} Run requested "
                        f"(time limit {config.solver.max_time_seconds:g}s)\n"
                    ),
                    files_json="[]",
                )
                db.add(run)
                db.commit()
                db.refresh(run)
                db.expunge(run)

            thread = threading.Thread(target=self._execute, args=(run.id, config), daemon=True)
            self._threads[run.id] = thread
            thread.start()
            return run

    def wait(self, run_id: str, timeout: float = 120.0) -> None:
        """Block until a run's thread finishes (used by tests)."""

        thread = self._threads.get(run_id)
        if thread is not None:
            thread.join(timeout)

    # -- worker -----------------------------------------------------------

    def _update(self, run_id: str, **values) -> None:
        log_line = values.pop("log_line", None)
        with self.session_factory() as db:
            run = db.get(TimetableRun, run_id)
            if run is None:
                return
            for key, value in values.items():
                setattr(run, key, value)
            if log_line:
                run.log = (run.log or "") + f"{_stamp()} {log_line}\n"
            db.commit()

    def _stage(self, run_id: str, stage: str, message: str) -> None:
        logger.info("[run %s] %s", run_id, message)
        self._update(run_id, stage=stage, log_line=message)

    def _execute(self, run_id: str, config: TimetableConfig) -> None:
        start = time.perf_counter()
        try:
            result_data, files, solver_result = self._run(run_id, config)
            report = result_data["score_report"]
            validation = result_data["validation"]
            values = {
                "status": "succeeded" if validation["is_valid"] else "failed",
                "stage": "done",
                "solver_status": solver_result.status,
                "total_weighted_penalty": report["total_weighted_penalty"],
                "result_json": json.dumps(result_data),
                "files_json": json.dumps(files),
            }
            if not validation["is_valid"]:
                values["error_summary"] = (
                    "The solver's timetable failed independent validation "
                    f"({validation['conflicts']} conflicts, {len(validation['violations'])} "
                    "violations). This indicates a modelling bug; please report it."
                )
                values["error_detail"] = "\n".join(
                    f"{item['reason']}: {item['message']}" for item in validation["violations"]
                )
            self._update(
                run_id,
                log_line=(
                    f"Finished: {values['status']} (penalty {report['total_weighted_penalty']})"
                ),
                **values,
            )
        except RunFailure as failure:
            logger.warning("[run %s] failed: %s\n%s", run_id, failure.summary, failure.detail)
            self._update(
                run_id,
                status="failed",
                error_summary=failure.summary,
                error_detail=failure.detail,
                log_line=f"FAILED: {failure.summary}",
            )
        except Exception as exc:  # noqa: BLE001 - every failure is recorded
            logger.exception("[run %s] crashed", run_id)
            self._update(
                run_id,
                status="failed",
                error_summary=f"Unexpected error: {type(exc).__name__}: {exc}",
                error_detail=traceback.format_exc(),
                log_line=f"FAILED with unexpected error: {type(exc).__name__}: {exc}",
            )
        finally:
            self._update(
                run_id,
                finished_at=datetime.now(UTC),
                elapsed_seconds=time.perf_counter() - start,
            )
            self._threads.pop(run_id, None)

    def _run(self, run_id: str, config: TimetableConfig) -> tuple[dict, list[str], SolverResult]:
        self._stage(run_id, "loading", "Loading scheduling data from the database")

        with self.session_factory() as db:
            timetable_input = build_timetable_input_from_db(db, config)
            metadata = load_render_metadata(db)

        sessions = len(timetable_input.sessions)
        self._update(run_id, session_count=sessions)

        if not sessions:
            raise RunFailure(
                "There are no active teaching assignments to schedule.",
                "Import a data workbook on the Import page (or add assignments on the "
                "Teaching assignments page), then start a new run.",
            )

        self._stage(
            run_id,
            "solving",
            f"Loaded {sessions} sessions and {len(timetable_input.rooms or ())} rooms; "
            f"running pre-solve checks and CP-SAT (up to {config.solver.max_time_seconds:g}s)",
        )

        try:
            result = solve(SchedulingProblem(timetable_input=timetable_input), config)
        except (PreSolveError, EmptyDomainsError) as exc:
            items = getattr(exc, "diagnostics", [])
            raise RunFailure(
                f"Pre-solve checks found {len(items) or 'some'} problem(s) that make the "
                "timetable impossible. Fix the data or relax the listed constraints.",
                str(exc),
            ) from exc
        except InfeasibleTimetableError as exc:
            if exc.status == "INFEASIBLE":
                summary = (
                    "CP-SAT proved that no timetable satisfies all hard constraints. "
                    "Relax one of the enabled optional hard constraints or change the data."
                )
            else:
                summary = (
                    f"CP-SAT found no timetable within the time limit (status {exc.status}). "
                    "Increase the time limit or relax constraints."
                )
            raise RunFailure(summary, str(exc)) from exc

        self._stage(
            run_id,
            "validating",
            f"Solver finished: {result.status}, objective {result.objective_value}, "
            f"{result.wall_time_seconds:.1f}s; validating and scoring",
        )

        data = _result_payload(result, timetable_input, config, metadata)

        self._stage(run_id, "exporting", "Writing CSV / Excel / JSON exports")
        files = _write_exports(data, result, timetable_input, metadata, self.files_dir(run_id))
        data.pop("_payload", None)
        return data, files, result


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _group_parents(timetable_input: TimetableInput, metadata: tuple) -> dict[str, str | None]:
    _, group_metadata, *_ = metadata
    codes = {group_id: code for group_id, (code, _) in group_metadata.items()}
    return {
        codes[group_id]: codes.get(parent_id) if parent_id is not None else None
        for group_id, parent_id in (timetable_input.academic_group_parent_ids or {}).items()
        if group_id in codes
    }


def _result_payload(
    result: SolverResult,
    timetable_input: TimetableInput,
    config: TimetableConfig,
    metadata: tuple,
) -> dict:
    validation = validate_timetable(
        result.timetable,
        timetable_input.academic_group_parent_ids,
        timetable_input=timetable_input,
        config=config,
    )
    rows = build_score_report(result, timetable_input, config)
    metrics = headline_metrics(result.timetable, timetable_input, config)
    payload = score_report_payload(rows, result, metrics)
    entries = view_entries_from_metadata(metadata, result.timetable)
    times = timetable_input.period_times or {}
    periods = timetable_input.periods_per_day

    return {
        "_payload": (payload, entries),
        "score_report": payload,
        "validation": {
            "is_valid": validation.is_valid,
            "conflicts": len(validation.conflicts),
            "violations": [
                {"reason": item.reason.value, "message": item.message}
                for item in validation.violations[:100]
            ],
        },
        "diagnostics": [str(item) for item in result.diagnostics],
        "calendar": {
            "days": [day.value for day in timetable_input.days],
            "periods": [
                {
                    "number": number,
                    "start": _hhmm(times[number][0]) if number in times else None,
                    "end": _hhmm(times[number][1]) if number in times else None,
                }
                for number in range(1, periods + 1)
            ],
            "lunch_after_period": timetable_input.lunch_after_period,
        },
        "group_parents": _group_parents(timetable_input, metadata),
        "entries": [
            {
                "session_id": entry.session_id,
                "day": entry.day.value,
                "start_period": entry.start_period,
                "end_period": entry.end_period,
                "subject": entry.subject_name,
                "course_code": entry.course_code,
                "group_code": entry.academic_group_code,
                "group_name": entry.academic_group_name,
                "faculty": entry.faculty_name,
                "room": entry.room_name,
            }
            for entry in entries
        ],
    }


def _write_exports(data, result, timetable_input, metadata, output_dir: Path) -> list[str]:
    payload, entries = data["_payload"]
    days = [day.value for day in timetable_input.days]
    group_parents = data["group_parents"]

    output_dir.mkdir(parents=True, exist_ok=True)
    write_score_report(payload, output_dir / "score_report.json")
    export_timetable_csv(entries, output_dir / "timetable_master.csv")
    export_master_workbook(
        entries, output_dir / "timetable_master.xlsx", summary_rows=summary_sheet_rows(payload)
    )
    export_day_workbook(entries, output_dir / "timetable_by_day.xlsx")
    export_faculty_workbook(entries, output_dir / "timetable_by_faculty.xlsx")
    for by in ("group", "faculty", "room"):
        export_grid_workbook(
            entries,
            output_dir / f"grid_by_{by}.xlsx",
            by=by,
            days=days,
            periods_per_day=timetable_input.periods_per_day,
            group_parents=group_parents,
        )
    return [name for name in EXPORT_FILES if (output_dir / name).exists()]


@lru_cache
def _default_run_manager() -> RunManager:
    return RunManager(get_session_factory(), Path(settings.output_dir))


def get_run_manager() -> RunManager:
    """FastAPI dependency; tests override it with an isolated manager."""

    return _default_run_manager()


# ---------------------------------------------------------------------------
# Config routes
# ---------------------------------------------------------------------------


def _config_payload(config: TimetableConfig) -> dict:
    return {
        "config": config.model_dump(mode="json"),
        "summary": config.summary_lines(),
        "enabled_optional_hard_constraints": config.enabled_optional_hard_constraints(),
    }


@router.get("/config")
def get_config(config: TimetableConfig = Depends(get_timetable_config)) -> dict:
    return _config_payload(config)


@router.get("/config/schema")
def get_config_schema() -> dict:
    """JSON schema of the config; drives the editor in the web UI."""

    return TimetableConfig.model_json_schema()


@router.put("/config")
def update_config(
    payload: Annotated[dict, Body()],
    store: ConfigStore = Depends(get_config_store),
) -> dict:
    try:
        config = TimetableConfig.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=[
                {"loc": ["body", *error["loc"]], "msg": error["msg"]}
                for error in exc.errors(include_url=False)
            ],
        ) from exc
    saved = store.save(config)
    logger.info("Timetable configuration updated (%s)", store.path)
    return _config_payload(saved)


@router.post("/config/reset")
def reset_config(store: ConfigStore = Depends(get_config_store)) -> dict:
    logger.info("Timetable configuration reset to defaults (%s)", store.path)
    return _config_payload(store.reset())


# ---------------------------------------------------------------------------
# Run routes
# ---------------------------------------------------------------------------


def _session(manager: RunManager) -> Session:
    return manager.session_factory()


@router.get("/runs")
def list_runs(
    status_filter: str | None = None,
    limit: int = 100,
    manager: RunManager = Depends(get_run_manager),
) -> list[dict]:
    with _session(manager) as db:
        stmt = select(TimetableRun).order_by(TimetableRun.started_at.desc()).limit(limit)
        if status_filter:
            stmt = stmt.where(TimetableRun.status == status_filter)
        return [run_summary(run) for run in db.scalars(stmt).all()]


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
def start_run(
    payload: RunRequest | None = None,
    config: TimetableConfig = Depends(get_timetable_config),
    manager: RunManager = Depends(get_run_manager),
) -> dict:
    if payload is not None and payload.max_time_seconds is not None:
        config = config.model_copy(
            update={
                "solver": config.solver.model_copy(
                    update={"max_time_seconds": payload.max_time_seconds}
                )
            }
        )
    return run_summary(manager.start(config))


@router.get("/runs/{run_id}")
def get_run(run_id: str, manager: RunManager = Depends(get_run_manager)) -> dict:
    with _session(manager) as db:
        run = db.get(TimetableRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        return run_detail(run)


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, manager: RunManager = Depends(get_run_manager)) -> None:
    with _session(manager) as db:
        run = db.get(TimetableRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        if run.status == "running":
            raise HTTPException(status_code=409, detail="A running run cannot be deleted")
        db.delete(run)
        db.commit()

    directory = manager.files_dir(run_id)
    for name in EXPORT_FILES:
        (directory / name).unlink(missing_ok=True)
    if directory.exists() and not any(directory.iterdir()):
        directory.rmdir()


@router.get("/runs/{run_id}/files/{name}")
def download_run_file(
    run_id: str,
    name: str,
    manager: RunManager = Depends(get_run_manager),
) -> FileResponse:
    with _session(manager) as db:
        run = db.get(TimetableRun, run_id)
        files = json.loads(run.files_json or "[]") if run is not None else []
    path = manager.files_dir(run_id) / name
    if name not in files or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=name)
