"""Timetable generation endpoints.

A run loads the scheduling input from the database inside the request,
then solves in a background thread (CP-SAT can take minutes). Clients poll
``GET /timetable/runs/{id}``. Runs are kept in memory; their export files
are written to ``<output_dir>/runs/<id>/``.
"""

from __future__ import annotations

import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1._common import get_timetable_config
from app.core.timetable_config import TimetableConfig
from app.db.session import get_db
from app.domain.db_input import build_timetable_input_from_db
from app.domain.db_render_data import load_render_metadata
from app.domain.diagnostics import PreSolveError
from app.domain.problem import SchedulingProblem
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
from app.optimisation.solver import InfeasibleTimetableError, solve

router = APIRouter(prefix="/timetable", tags=["Timetable"])

RunStatus = Literal["running", "succeeded", "infeasible", "failed"]

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


@dataclass
class TimetableRun:
    id: str
    status: RunStatus
    started_at: datetime
    max_time_seconds: float
    session_count: int
    finished_at: datetime | None = None
    elapsed_seconds: float = 0.0
    error: str | None = None
    result: dict | None = None
    files: list[str] = field(default_factory=list)
    _start: float = field(default_factory=time.perf_counter, repr=False)

    def summary(self) -> dict:
        elapsed = (
            self.elapsed_seconds if self.status != "running" else time.perf_counter() - self._start
        )
        report = (self.result or {}).get("score_report") or {}
        return {
            "id": self.id,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "elapsed_seconds": round(elapsed, 2),
            "max_time_seconds": self.max_time_seconds,
            "session_count": self.session_count,
            "solver_status": report.get("status"),
            "total_weighted_penalty": report.get("total_weighted_penalty"),
            "error": self.error,
        }

    def detail(self) -> dict:
        return {
            **self.summary(),
            "files": [{"name": name, "label": EXPORT_FILES[name]} for name in self.files],
            "result": self.result,
        }


class RunManager:
    """In-memory registry of solve runs (one active run at a time)."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self._runs: dict[str, TimetableRun] = {}
        self._lock = threading.Lock()

    def list(self) -> list[TimetableRun]:
        return sorted(self._runs.values(), key=lambda run: run.started_at, reverse=True)

    def get(self, run_id: str) -> TimetableRun | None:
        return self._runs.get(run_id)

    def start(
        self,
        timetable_input: TimetableInput,
        config: TimetableConfig,
        metadata: tuple,
    ) -> TimetableRun:
        with self._lock:
            if any(run.status == "running" for run in self._runs.values()):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A timetable run is already in progress",
                )
            run = TimetableRun(
                id=uuid.uuid4().hex[:12],
                status="running",
                started_at=datetime.now(UTC),
                max_time_seconds=config.solver.max_time_seconds,
                session_count=len(timetable_input.sessions),
            )
            self._runs[run.id] = run

        thread = threading.Thread(
            target=self._execute,
            args=(run, timetable_input, config, metadata),
            daemon=True,
        )
        thread.start()
        return run

    def wait(self, run_id: str, timeout: float = 60.0) -> TimetableRun:
        """Block until a run finishes (used by tests)."""

        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            run = self._runs[run_id]
            if run.status != "running":
                return run
            time.sleep(0.05)
        raise TimeoutError(run_id)

    # -- worker -----------------------------------------------------------

    def _execute(self, run, timetable_input, config, metadata) -> None:
        try:
            run.result, run.files = _solve_and_export(
                timetable_input, config, metadata, self.output_dir / "runs" / run.id
            )
            run.status = "succeeded"
        except (PreSolveError, InfeasibleTimetableError) as exc:
            run.status = "infeasible"
            run.error = str(exc)
        except Exception as exc:  # noqa: BLE001 - surfaced to the client
            run.status = "failed"
            run.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=5)}"
        finally:
            run.finished_at = datetime.now(UTC)
            run.elapsed_seconds = time.perf_counter() - run._start


def _solve_and_export(
    timetable_input: TimetableInput,
    config: TimetableConfig,
    metadata: tuple,
    output_dir: Path,
) -> tuple[dict, list[str]]:
    result = solve(SchedulingProblem(timetable_input=timetable_input), config)

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

    _, group_metadata, *_ = metadata
    codes = {group_id: code for group_id, (code, _) in group_metadata.items()}
    group_parents = {
        codes[group_id]: codes.get(parent_id) if parent_id is not None else None
        for group_id, parent_id in (timetable_input.academic_group_parent_ids or {}).items()
        if group_id in codes
    }
    days = [day.value for day in timetable_input.days]
    periods = timetable_input.periods_per_day

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
            periods_per_day=periods,
            group_parents=group_parents,
        )

    times = timetable_input.period_times or {}
    data = {
        "score_report": payload,
        "validation": {
            "is_valid": validation.is_valid,
            "conflicts": len(validation.conflicts),
            "violations": [
                {"reason": item.reason.value, "message": item.message}
                for item in validation.violations[:50]
            ],
        },
        "diagnostics": [str(item) for item in result.diagnostics],
        "calendar": {
            "days": days,
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
        "group_parents": group_parents,
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
    return data, [name for name in EXPORT_FILES if (output_dir / name).exists()]


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


@lru_cache
def _default_run_manager() -> RunManager:
    return RunManager(Path("output"))


def get_run_manager() -> RunManager:
    """FastAPI dependency; tests override it with an isolated manager."""

    return _default_run_manager()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/config")
def get_config(config: TimetableConfig = Depends(get_timetable_config)) -> dict:
    return {
        "config": config.model_dump(mode="json"),
        "summary": config.summary_lines(),
        "enabled_optional_hard_constraints": config.enabled_optional_hard_constraints(),
    }


@router.get("/runs")
def list_runs(manager: RunManager = Depends(get_run_manager)) -> list[dict]:
    return [run.summary() for run in manager.list()]


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
def start_run(
    payload: RunRequest | None = None,
    db: Session = Depends(get_db),
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

    timetable_input = build_timetable_input_from_db(db, config)

    if not timetable_input.sessions:
        raise HTTPException(
            status_code=422,
            detail="There are no active teaching assignments to schedule",
        )

    metadata = load_render_metadata(db)
    return manager.start(timetable_input, config, metadata).summary()


@router.get("/runs/{run_id}")
def get_run(run_id: str, manager: RunManager = Depends(get_run_manager)) -> dict:
    run = manager.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run.detail()


@router.get("/runs/{run_id}/files/{name}")
def download_run_file(
    run_id: str,
    name: str,
    manager: RunManager = Depends(get_run_manager),
) -> FileResponse:
    run = manager.get(run_id)
    if run is None or name not in run.files:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        manager.output_dir / "runs" / run_id / name,
        filename=name,
    )
