"""Post-solve score report.

For every constraint the report shows its mode and weight, the raw penalty
from the independent calculator, the weighted penalty and the value of the
solver's own penalty variable. A mismatch between the calculator and the
solver flags a modelling bug.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.core.timetable_config import SOFT_CONSTRAINT_IDS, TimetableConfig
from app.domain.schedule import Timetable
from app.domain.timetable import TimetableInput
from app.optimisation.penalties import (
    TimetableFacts,
    calculate_all_penalties,
    constraint_mode,
    faculty_gaps,
    lunch_crossings,
    room_stability,
    student_gaps,
    subject_spreading,
)
from app.optimisation.solver import SolverResult


@dataclass(frozen=True)
class ScoreRow:
    key: str
    constraint_id: str
    mode: str
    weight: int
    raw_penalty: int
    weighted_penalty: int
    solver_penalty: int | None

    @property
    def mismatch(self) -> bool:
        return self.solver_penalty is not None and self.solver_penalty != self.raw_penalty


def build_score_report(
    result: SolverResult,
    timetable_input: TimetableInput,
    config: TimetableConfig,
) -> list[ScoreRow]:
    raw = calculate_all_penalties(result.timetable, timetable_input, config)
    solver_values = {item.key: item.value for item in result.penalties}
    rows = []

    for key, value in raw.items():
        mode, weight = constraint_mode(config, key)
        rows.append(
            ScoreRow(
                key=key,
                constraint_id=SOFT_CONSTRAINT_IDS.get(key, ""),
                mode=mode,
                weight=weight,
                raw_penalty=value,
                weighted_penalty=weight * value if mode == "soft" else 0,
                solver_penalty=solver_values.get(key),
            )
        )

    return rows


def headline_metrics(
    timetable: Timetable,
    timetable_input: TimetableInput,
    config: TimetableConfig,
) -> dict[str, int]:
    """Before/after metrics named in the change specification."""

    facts = TimetableFacts.build(timetable, timetable_input, config)
    last_period = timetable_input.periods_per_day

    return {
        "student_gaps": student_gaps(facts),
        "same_day_subject_repeats": subject_spreading(facts),
        "sessions_across_lunch": lunch_crossings(facts),
        f"sessions_in_P{last_period}": sum(
            1 for placement in timetable.placements if placement.end_period >= last_period
        ),
        "faculty_gaps": faculty_gaps(facts),
        "room_changes_per_group_day": room_stability(facts),
    }


def format_score_report(rows: list[ScoreRow]) -> str:
    header = (
        f"{'constraint':<30} {'id':<4} {'mode':<5} {'weight':>6} "
        f"{'raw':>6} {'weighted':>9} {'solver':>7}  check"
    )
    lines = [header, "-" * len(header)]

    for row in rows:
        solver = "-" if row.solver_penalty is None else str(row.solver_penalty)
        check = "MISMATCH" if row.mismatch else ("ok" if row.solver_penalty is not None else "")
        lines.append(
            f"{row.key:<30} {row.constraint_id:<4} {row.mode:<5} {row.weight:>6} "
            f"{row.raw_penalty:>6} {row.weighted_penalty:>9} {solver:>7}  {check}"
        )

    total = sum(row.weighted_penalty for row in rows)
    lines.append("-" * len(header))
    lines.append(f"{'total weighted penalty':<30} {'':<4} {'':<5} {'':>6} {'':>6} {total:>9}")
    return "\n".join(lines)


def score_report_payload(
    rows: list[ScoreRow],
    result: SolverResult,
    metrics: dict[str, int],
) -> dict:
    return {
        "status": result.status,
        "objective_value": result.objective_value,
        "best_bound": result.best_bound,
        "wall_time_seconds": round(result.wall_time_seconds, 3),
        "build_time_seconds": round(result.build_time_seconds, 3),
        "model_stats": result.model_stats,
        "total_weighted_penalty": sum(row.weighted_penalty for row in rows),
        "mismatches": [row.key for row in rows if row.mismatch],
        "metrics": metrics,
        "constraints": [{**asdict(row), "mismatch": row.mismatch} for row in rows],
    }


def write_score_report(payload: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def summary_sheet_rows(payload: dict) -> list[list]:
    """Rows for the "Summary" worksheet of the master workbook."""

    rows: list[list] = [
        ["Status", payload["status"]],
        ["Objective", payload["objective_value"]],
        ["Best bound", payload["best_bound"]],
        ["Solve time (s)", payload["wall_time_seconds"]],
        ["Total weighted penalty", payload["total_weighted_penalty"]],
        [],
        ["Metric", "Value"],
        *([key, value] for key, value in payload["metrics"].items()),
        [],
        ["Constraint", "ID", "Mode", "Weight", "Raw", "Weighted", "Solver", "Mismatch"],
    ]

    rows.extend(
        [
            item["key"],
            item["constraint_id"],
            item["mode"],
            item["weight"],
            item["raw_penalty"],
            item["weighted_penalty"],
            item["solver_penalty"],
            "YES" if item["mismatch"] else "",
        ]
        for item in payload["constraints"]
    )
    return rows
