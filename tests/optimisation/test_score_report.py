from app.optimisation.score_report import (
    build_score_report,
    format_score_report,
    headline_metrics,
    score_report_payload,
    summary_sheet_rows,
)
from app.optimisation.solver import solve
from tests.optimisation import helpers as h


def test_score_report_rows_and_payload():
    problem = h.problem([h.session(group=1, faculty=1), h.session(group=1, faculty=2)])
    config = h.config_with(h.avoid(2, 3), ("soft", "student_gaps", {"enabled": True, "weight": 5}))
    result = solve(problem, config)

    rows = build_score_report(result, problem.timetable_input, config)
    by_key = {row.key: row for row in rows}

    assert by_key["student_gaps"].mode == "soft"
    assert by_key["student_gaps"].solver_penalty == by_key["student_gaps"].raw_penalty == 0
    assert by_key["faculty_gaps"].mode == "off"
    assert by_key["faculty_gaps"].solver_penalty is None
    assert not any(row.mismatch for row in rows)

    text = format_score_report(rows)
    assert "student_gaps" in text and "MISMATCH" not in text

    metrics = headline_metrics(result.timetable, problem.timetable_input, config)
    assert metrics["student_gaps"] == 0
    assert "sessions_in_P4" in metrics

    payload = score_report_payload(rows, result, metrics)
    assert payload["mismatches"] == []
    assert payload["status"] in {"OPTIMAL", "FEASIBLE"}
    assert summary_sheet_rows(payload)[0] == ["Status", payload["status"]]
