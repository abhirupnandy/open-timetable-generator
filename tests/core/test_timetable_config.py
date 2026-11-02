from __future__ import annotations

import pytest

from app.core.timetable_config import (
    DEFAULT_CONFIG_PATH,
    ConstraintMode,
    TimetableConfig,
    TimetableConfigError,
    load_timetable_config,
    parse_timetable_config,
)


def test_shipped_config_matches_builtin_defaults():
    assert DEFAULT_CONFIG_PATH.exists()
    assert load_timetable_config() == TimetableConfig()


def test_calendar_derives_periods_and_times():
    calendar = TimetableConfig().calendar
    assert calendar.periods_per_day == 8
    assert calendar.period_times[1] == (8 * 60 + 20, 9 * 60 + 20)
    assert calendar.lunch_after_period == 4
    assert [(slot.day, slot.period) for slot in calendar.blocked_slots] == [("MONDAY", 6)]


@pytest.mark.parametrize(
    "data",
    [
        {"soft": {"student_gap": {"enabled": True}}},  # typo in key
        {"soft": {"student_gaps": {"enabled": True, "wieght": 3}}},  # typo in param
        {"unknown_section": {}},
        {"hard": {"faculty_weekly_cap": {"hours": {"LECTURER": 3}}}},
    ],
)
def test_unknown_keys_are_rejected(data):
    with pytest.raises(TimetableConfigError, match="Extra inputs are not permitted"):
        parse_timetable_config(data)


def test_negative_weight_is_rejected():
    with pytest.raises(TimetableConfigError, match="greater than or equal to 0"):
        parse_timetable_config({"soft": {"faculty_gaps": {"weight": -1}}})


def test_unknown_period_in_preference_ranges_is_rejected():
    with pytest.raises(TimetableConfigError, match="unknown periods \\[9\\]"):
        parse_timetable_config(
            {"soft": {"faculty_time_preference": {"ranges": {"EVENING": [8, 9]}}}}
        )


def test_unknown_period_in_avoid_rule_is_rejected():
    with pytest.raises(TimetableConfigError, match="unknown period 12"):
        parse_timetable_config({"soft": {"avoid_periods": {"rules": [{"period": 12}]}}})


def test_blocked_slot_must_exist():
    with pytest.raises(TimetableConfigError, match="does not exist"):
        parse_timetable_config({"calendar": {"blocked_slots": [{"day": "MONDAY", "period": 9}]}})


def test_periods_must_be_numbered_in_order():
    periods = [
        {"number": 1, "start": "08:00", "end": "09:00"},
        {"number": 3, "start": "09:00", "end": "10:00"},
    ]
    with pytest.raises(TimetableConfigError, match="numbered 1..N"):
        parse_timetable_config({"calendar": {"periods": periods, "blocked_slots": []}})


def test_invalid_time_and_mode_are_rejected():
    with pytest.raises(TimetableConfigError):
        parse_timetable_config(
            {"calendar": {"periods": [{"number": 1, "start": "8am", "end": "09:00"}]}}
        )
    with pytest.raises(TimetableConfigError):
        parse_timetable_config({"constraints": {"faculty_max_consecutive": {"mode": "maybe"}}})


def test_min_free_cannot_exceed_periods():
    with pytest.raises(TimetableConfigError, match="min_free"):
        parse_timetable_config({"soft": {"student_min_free_periods": {"min_free": 9}}})


def test_load_from_file_and_missing_file(tmp_path):
    path = tmp_path / "timetable.toml"
    path.write_text('[constraints.no_session_across_lunch]\nmode = "hard"\n')
    config = load_timetable_config(path)
    assert config.constraints.no_session_across_lunch.mode == ConstraintMode.HARD

    with pytest.raises(TimetableConfigError, match="not found"):
        load_timetable_config(tmp_path / "missing.toml")

    path.write_text("not = [valid")
    with pytest.raises(TimetableConfigError, match="Invalid TOML"):
        load_timetable_config(path)


def test_summary_and_enabled_hard_constraints():
    config = TimetableConfig()
    summary = "\n".join(config.summary_lines())
    assert "student_gaps" in summary and "weight=100" in summary
    assert "faculty_daily_span" in config.enabled_optional_hard_constraints()
