"""Seeded end-to-end solve on a database imported from samples/sample_data.xlsx.

Uses a shorter time limit than production; the timetable only needs to be
feasible here. Build/solve time and peak memory are printed (run with -s).
"""

from __future__ import annotations

import resource

import pytest
from sqlalchemy import select

from app.core.timetable_config import TimetableConfig, load_timetable_config
from app.db.models import TeachingAssignment
from app.domain.db_input import build_timetable_input_from_db
from app.domain.problem import SchedulingProblem
from app.domain.timetable_view_builder import build_timetable_view_entries
from app.domain.validator import validate_timetable
from app.optimisation.score_report import build_score_report
from app.optimisation.solver import solve

TIME_LIMIT_SECONDS = 20


def _config(all_optional_off: bool = False) -> TimetableConfig:
    data = load_timetable_config().model_dump(mode="json")
    data["solver"]["max_time_seconds"] = TIME_LIMIT_SECONDS

    if all_optional_off:
        for key in data["soft"]:
            data["soft"][key]["enabled"] = False
        for key in data["constraints"]:
            data["constraints"][key]["mode"] = "off"
        for key in data["hard"]:
            data["hard"][key]["enabled"] = False

    return TimetableConfig.model_validate(data)


@pytest.fixture(scope="module")
def seeded(seeded_session_factory):
    config = _config()

    with seeded_session_factory() as db:
        assignments = tuple(
            db.scalars(
                select(TeachingAssignment).where(TeachingAssignment.is_active.is_(True))
            ).all()
        )
        timetable_input = build_timetable_input_from_db(db, config)

    result = solve(SchedulingProblem(timetable_input=timetable_input), config)
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(
        f"\n[seeded] status={result.status} build={result.build_time_seconds:.2f}s "
        f"solve={result.wall_time_seconds:.2f}s peak_rss={peak_mb:.0f}MB {result.model_stats}"
    )
    return assignments, timetable_input, result, config, seeded_session_factory


def test_seeded_database_produces_timetable(seeded) -> None:
    assignments, timetable_input, result, *_ = seeded

    assert len(assignments) == 80
    assert len(timetable_input.sessions) == 173
    assert len(result.timetable.placements) == 173

    session_ids = {placement.session.id for placement in result.timetable.placements}
    assert len(session_ids) == 173


def test_seeded_timetable_is_valid_and_scores_match(seeded) -> None:
    _, timetable_input, result, config, _ = seeded

    validation = validate_timetable(
        result.timetable,
        timetable_input.academic_group_parent_ids,
        timetable_input=timetable_input,
        config=config,
    )
    assert validation.is_valid, (validation.conflicts[:5], validation.violations[:5])

    rows = build_score_report(result, timetable_input, config)
    assert [row.key for row in rows if row.mismatch] == []


def test_seeded_timetable_builds_view_entries(seeded) -> None:
    _, _, result, _, factory = seeded

    with factory() as db:
        entries = build_timetable_view_entries(db, result.timetable)

    assert len(entries) == 173
    assert len({entry.session_id for entry in entries}) == 173

    for entry in entries:
        assert entry.subject_name
        assert entry.course_code
        assert entry.course_name
        assert entry.academic_group_code
        assert entry.academic_group_name
        assert entry.faculty_name
        assert entry.start_period > 0
        assert entry.end_period >= entry.start_period


def test_seeded_problem_is_feasible_with_all_optional_constraints_disabled(
    seeded_session_factory,
) -> None:
    config = _config(all_optional_off=True)

    with seeded_session_factory() as db:
        timetable_input = build_timetable_input_from_db(db, config)

    result = solve(SchedulingProblem(timetable_input=timetable_input), config)
    assert len(result.timetable.placements) == 173
    assert result.penalties == ()
