"""Timetable constraint and solver configuration.

The configuration is stored as TOML (``config/timetable.toml`` by default)
and validated with Pydantic. Unknown keys are rejected so that typos in
constraint names or parameters fail loudly instead of being ignored.

Every optional constraint uses one of three shapes:

* hard-only optional: ``enabled`` plus parameters;
* flexible: ``mode = "off" | "soft" | "hard"`` plus ``weight``;
* soft-only: ``enabled``, ``weight`` plus parameters.

Non-negotiable hard constraints (each session placed exactly once, no
faculty/student/room overlap, session fits in the day, room type,
room capacity, online/in-person rules) are always on and are therefore
not represented here.
"""

from __future__ import annotations

import json
import re
import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "timetable.toml"

WEEKDAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY")
DESIGNATIONS = ("PROFESSOR", "ASSOCIATE_PROFESSOR", "ASSISTANT_PROFESSOR", "PHD_SCHOLAR")
SUBJECT_TYPES = ("LECTURE", "LAB", "TUTORIAL")

_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

Weekday = Literal["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
SubjectTypeName = Literal["LECTURE", "LAB", "TUTORIAL"]


class ConstraintMode(StrEnum):
    OFF = "off"
    SOFT = "soft"
    HARD = "hard"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# TOML has no null. Fields where "not set" differs from the default accept
# the string "none", which the config writer emits for None.
NONE_SENTINEL = "none"


def _none_sentinel(value: object) -> object:
    if isinstance(value, str) and value.strip().lower() == NONE_SENTINEL:
        return None
    return value


def _minutes(value: str) -> int:
    match = _TIME_PATTERN.match(value)

    if match is None:
        raise ValueError(f"Invalid time {value!r}; expected HH:MM")

    return int(match.group(1)) * 60 + int(match.group(2))


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------


class PeriodConfig(_Strict):
    number: int = Field(ge=1)
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _check_time(cls, value: str) -> str:
        _minutes(value)
        return value

    @model_validator(mode="after")
    def _check_order(self) -> PeriodConfig:
        if _minutes(self.end) <= _minutes(self.start):
            raise ValueError(f"Period {self.number} must end after it starts")
        return self

    @property
    def start_minutes(self) -> int:
        return _minutes(self.start)

    @property
    def end_minutes(self) -> int:
        return _minutes(self.end)


class BlockedSlotConfig(_Strict):
    day: Weekday
    period: int = Field(ge=1)
    label: str = ""


def _default_periods() -> list[PeriodConfig]:
    times = [
        ("08:20", "09:20"),
        ("09:25", "10:25"),
        ("10:30", "11:30"),
        ("11:35", "12:35"),
        ("13:45", "14:45"),
        ("14:50", "15:50"),
        ("15:55", "16:55"),
        ("17:00", "18:00"),
    ]
    return [
        PeriodConfig(number=index, start=start, end=end)
        for index, (start, end) in enumerate(times, start=1)
    ]


class CalendarConfig(_Strict):
    days: list[Weekday] = Field(
        default_factory=lambda: ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
    )
    lunch_after_period: int | None = 4
    periods: list[PeriodConfig] = Field(default_factory=_default_periods)
    blocked_slots: list[BlockedSlotConfig] = Field(
        default_factory=lambda: [BlockedSlotConfig(day="MONDAY", period=6, label="TREP")]
    )

    _lunch_none = field_validator("lunch_after_period", mode="before")(
        classmethod(lambda cls, value: _none_sentinel(value))
    )

    @model_validator(mode="after")
    def _validate(self) -> CalendarConfig:
        if not self.days:
            raise ValueError("calendar.days must contain at least one day")

        if len(set(self.days)) != len(self.days):
            raise ValueError("calendar.days contains duplicates")

        if not self.periods:
            raise ValueError("calendar.periods must contain at least one period")

        numbers = [period.number for period in self.periods]

        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError(f"calendar.periods must be numbered 1..N in order; got {numbers}")

        for previous, current in zip(self.periods, self.periods[1:], strict=False):
            if current.start_minutes < previous.end_minutes:
                raise ValueError(
                    f"Period {current.number} starts before period {previous.number} ends"
                )

        if self.lunch_after_period is not None and not (
            1 <= self.lunch_after_period < len(self.periods)
        ):
            raise ValueError(
                "calendar.lunch_after_period must be between 1 and the last period - 1"
            )

        for slot in self.blocked_slots:
            if slot.day not in self.days:
                raise ValueError(f"Blocked slot day {slot.day} is not a calendar day")
            if slot.period > len(self.periods):
                raise ValueError(f"Blocked slot period {slot.period} does not exist")

        return self

    @property
    def periods_per_day(self) -> int:
        return len(self.periods)

    @property
    def period_times(self) -> dict[int, tuple[int, int]]:
        return {
            period.number: (period.start_minutes, period.end_minutes) for period in self.periods
        }


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------


class SolverConfig(_Strict):
    max_time_seconds: float = Field(default=120.0, gt=0)
    workers: int = Field(default=8, ge=1)
    log_progress: bool = False
    random_seed: int | None = None

    _seed_none = field_validator("random_seed", mode="before")(
        classmethod(lambda cls, value: _none_sentinel(value))
    )


# ---------------------------------------------------------------------------
# Optional hard constraints
# ---------------------------------------------------------------------------


class DesignationHours(_Strict):
    PROFESSOR: int | None = Field(default=None, ge=0)
    ASSOCIATE_PROFESSOR: int | None = Field(default=None, ge=0)
    ASSISTANT_PROFESSOR: int | None = Field(default=None, ge=0)
    PHD_SCHOLAR: int | None = Field(default=None, ge=0)

    _hours_none = field_validator(*DESIGNATIONS, mode="before")(
        classmethod(lambda cls, value: _none_sentinel(value))
    )

    def for_designation(self, designation: str) -> int | None:
        if designation not in DESIGNATIONS:
            raise ValueError(f"Unsupported faculty designation: {designation!r}")
        return getattr(self, designation)

    def as_dict(self) -> dict[str, int]:
        """Designations with a configured (non-zero) number of hours."""

        return {
            designation: hours
            for designation in DESIGNATIONS
            if (hours := getattr(self, designation))
        }


class FacultyDailySpanConfig(_Strict):
    enabled: bool = True
    max_minutes: int = Field(default=480, gt=0)


class FacultyWeeklyCapConfig(_Strict):
    enabled: bool = True
    hours: DesignationHours = Field(
        default_factory=lambda: DesignationHours(
            PROFESSOR=9,
            ASSOCIATE_PROFESSOR=11,
            ASSISTANT_PROFESSOR=13,
            PHD_SCHOLAR=8,
        )
    )


class FacultyWeeklyMinimumConfig(_Strict):
    enabled: bool = False
    hours: DesignationHours = Field(default_factory=lambda: DesignationHours(PROFESSOR=6))


class ToggleConfig(_Strict):
    enabled: bool = True


class RoleRestrictionsConfig(_Strict):
    """Allowed subject types per designation (designations not listed are unrestricted)."""

    enabled: bool = False
    PROFESSOR: list[SubjectTypeName] | None = None
    ASSOCIATE_PROFESSOR: list[SubjectTypeName] | None = None
    ASSISTANT_PROFESSOR: list[SubjectTypeName] | None = None
    PHD_SCHOLAR: list[SubjectTypeName] | None = Field(default_factory=lambda: ["LAB", "TUTORIAL"])

    _roles_none = field_validator(*DESIGNATIONS, mode="before")(
        classmethod(lambda cls, value: _none_sentinel(value))
    )

    def allowed_types(self, designation: str) -> frozenset[str] | None:
        if designation not in DESIGNATIONS:
            return None
        allowed = getattr(self, designation)
        return frozenset(allowed) if allowed is not None else None


class HardConfig(_Strict):
    faculty_daily_span: FacultyDailySpanConfig = Field(default_factory=FacultyDailySpanConfig)
    faculty_weekly_cap: FacultyWeeklyCapConfig = Field(default_factory=FacultyWeeklyCapConfig)
    faculty_weekly_minimum: FacultyWeeklyMinimumConfig = Field(
        default_factory=FacultyWeeklyMinimumConfig
    )
    locked_sessions: ToggleConfig = Field(default_factory=ToggleConfig)
    group_blocked_slots: ToggleConfig = Field(default_factory=ToggleConfig)
    role_restrictions: RoleRestrictionsConfig = Field(default_factory=RoleRestrictionsConfig)


# ---------------------------------------------------------------------------
# Flexible constraints (off / soft / hard)
# ---------------------------------------------------------------------------


class FlexibleConfig(_Strict):
    mode: ConstraintMode = ConstraintMode.OFF
    weight: int = Field(default=0, ge=0)


class MaxConsecutiveConfig(FlexibleConfig):
    max_periods: int = Field(default=3, ge=1)


class ConstraintsConfig(_Strict):
    no_session_across_lunch: FlexibleConfig = Field(
        default_factory=lambda: FlexibleConfig(mode=ConstraintMode.SOFT, weight=60)
    )
    faculty_max_consecutive: MaxConsecutiveConfig = Field(
        default_factory=lambda: MaxConsecutiveConfig(
            mode=ConstraintMode.SOFT, weight=40, max_periods=3
        )
    )
    student_max_consecutive: MaxConsecutiveConfig = Field(
        default_factory=lambda: MaxConsecutiveConfig(
            mode=ConstraintMode.OFF, weight=30, max_periods=4
        )
    )


# ---------------------------------------------------------------------------
# Soft constraints
# ---------------------------------------------------------------------------


class SoftConfig(_Strict):
    enabled: bool = True
    weight: int = Field(default=0, ge=0)


class MinFreeConfig(SoftConfig):
    min_free: int = Field(default=2, ge=0)


class MaxLecturesConfig(SoftConfig):
    max_lectures: int = Field(default=2, ge=0)


class PreferenceRanges(_Strict):
    MORNING: list[int] = Field(default_factory=lambda: [1, 2, 3, 4])
    AFTERNOON: list[int] = Field(default_factory=lambda: [5, 6, 7, 8])
    EVENING: list[int] = Field(default_factory=lambda: [7, 8])

    def as_dict(self) -> dict[str, frozenset[int]]:
        return {
            "MORNING": frozenset(self.MORNING),
            "AFTERNOON": frozenset(self.AFTERNOON),
            "EVENING": frozenset(self.EVENING),
        }


class TimePreferenceConfig(SoftConfig):
    ranges: PreferenceRanges = Field(default_factory=PreferenceRanges)


class AvoidPeriodRule(_Strict):
    period: int = Field(ge=1)
    penalty: int = Field(default=1, ge=0)
    subject_types: list[SubjectTypeName] | None = None
    days: list[Weekday] | None = None

    _filters_none = field_validator("subject_types", "days", mode="before")(
        classmethod(lambda cls, value: _none_sentinel(value))
    )


class AvoidPeriodsConfig(SoftConfig):
    rules: list[AvoidPeriodRule] = Field(default_factory=list)


class RoomSizeFitConfig(SoftConfig):
    waste_unit: int = Field(default=10, ge=1)


class DailyLoadConfig(SoftConfig):
    max_periods: int = Field(default=4, ge=0)


class StabilityConfig(SoftConfig):
    previous_timetable: str = "output/timetable_master.csv"
    room_change_penalty: int = Field(default=0, ge=0)


class SoftConstraintsConfig(_Strict):
    student_gaps: SoftConfig = Field(default_factory=lambda: SoftConfig(weight=100))
    student_min_free_periods: MinFreeConfig = Field(
        default_factory=lambda: MinFreeConfig(weight=90, min_free=2)
    )
    subject_spreading: SoftConfig = Field(default_factory=lambda: SoftConfig(weight=80))
    faculty_workload_balance: SoftConfig = Field(default_factory=lambda: SoftConfig(weight=70))
    faculty_max_lectures_per_day: MaxLecturesConfig = Field(
        default_factory=lambda: MaxLecturesConfig(weight=60, max_lectures=2)
    )
    faculty_time_preference: TimePreferenceConfig = Field(
        default_factory=lambda: TimePreferenceConfig(weight=50)
    )
    avoid_periods: AvoidPeriodsConfig = Field(
        default_factory=lambda: AvoidPeriodsConfig(
            weight=40,
            rules=[
                AvoidPeriodRule(period=8, penalty=2),
                AvoidPeriodRule(period=1, penalty=1, subject_types=["LAB"]),
            ],
        )
    )
    faculty_gaps: SoftConfig = Field(default_factory=lambda: SoftConfig(weight=75))
    room_stability: SoftConfig = Field(default_factory=lambda: SoftConfig(weight=30))
    subject_day_spacing: SoftConfig = Field(default_factory=lambda: SoftConfig(weight=35))
    group_daily_load_balance: SoftConfig = Field(default_factory=lambda: SoftConfig(weight=30))
    parallel_batch_labs: SoftConfig = Field(default_factory=lambda: SoftConfig(weight=25))
    room_size_fit: RoomSizeFitConfig = Field(
        default_factory=lambda: RoomSizeFitConfig(weight=10, waste_unit=10)
    )
    faculty_compact_days: SoftConfig = Field(
        default_factory=lambda: SoftConfig(enabled=False, weight=15)
    )
    consistent_subject_time: SoftConfig = Field(
        default_factory=lambda: SoftConfig(enabled=False, weight=10)
    )
    faculty_daily_load: DailyLoadConfig = Field(
        default_factory=lambda: DailyLoadConfig(weight=30, max_periods=4)
    )
    online_at_day_edges: SoftConfig = Field(default_factory=lambda: SoftConfig(weight=20))
    faculty_preferred_day_off: SoftConfig = Field(
        default_factory=lambda: SoftConfig(enabled=False, weight=40)
    )
    stability_vs_previous: StabilityConfig = Field(
        default_factory=lambda: StabilityConfig(enabled=False, weight=50)
    )


# Mapping from config keys to the S-numbers already used in the codebase.
# Keys without an established S-number are intentionally left unmapped
# (see the design document for S5-S10, S12, S13).
SOFT_CONSTRAINT_IDS: dict[str, str] = {
    "student_gaps": "S1",
    "faculty_workload_balance": "S2",
    "faculty_time_preference": "S3",
    "subject_spreading": "S4",
    "faculty_max_lectures_per_day": "S11",
    "student_min_free_periods": "S14",
}


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


class TimetableConfig(_Strict):
    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
    solver: SolverConfig = Field(default_factory=SolverConfig)
    hard: HardConfig = Field(default_factory=HardConfig)
    constraints: ConstraintsConfig = Field(default_factory=ConstraintsConfig)
    soft: SoftConstraintsConfig = Field(default_factory=SoftConstraintsConfig)

    @model_validator(mode="after")
    def _validate_periods(self) -> TimetableConfig:
        valid_periods = set(range(1, self.calendar.periods_per_day + 1))

        for name, periods in self.soft.faculty_time_preference.ranges.as_dict().items():
            unknown = sorted(set(periods) - valid_periods)
            if unknown:
                raise ValueError(
                    f"soft.faculty_time_preference.ranges.{name} uses unknown periods {unknown}"
                )

        if self.soft.student_min_free_periods.min_free > self.calendar.periods_per_day:
            raise ValueError(
                "soft.student_min_free_periods.min_free cannot exceed the number of periods"
            )

        for rule in self.soft.avoid_periods.rules:
            if rule.period not in valid_periods:
                raise ValueError(f"soft.avoid_periods rule uses unknown period {rule.period}")
            for day in rule.days or ():
                if day not in self.calendar.days:
                    raise ValueError(f"soft.avoid_periods rule uses unknown day {day}")

        return self

    # -- convenience --------------------------------------------------------

    def soft_items(self) -> list[tuple[str, SoftConfig]]:
        return [(key, getattr(self.soft, key)) for key in SoftConstraintsConfig.model_fields]

    def flexible_items(self) -> list[tuple[str, FlexibleConfig]]:
        return [(key, getattr(self.constraints, key)) for key in ConstraintsConfig.model_fields]

    def hard_items(self) -> list[tuple[str, BaseModel]]:
        return [(key, getattr(self.hard, key)) for key in HardConfig.model_fields]

    def enabled_optional_hard_constraints(self) -> list[str]:
        """Names of optional hard rules that are switched on (for infeasibility reports)."""

        enabled = [key for key, item in self.hard_items() if getattr(item, "enabled", False)]
        enabled.extend(
            f"constraints.{key} (hard)"
            for key, item in self.flexible_items()
            if item.mode == ConstraintMode.HARD
        )
        return enabled

    def summary_lines(self) -> list[str]:
        """Human-readable summary of enabled constraints and weights."""

        lines = ["Optional hard constraints:"]
        for key, item in self.hard_items():
            state = "on" if getattr(item, "enabled", False) else "off"
            lines.append(f"  {key:<32} {state}")

        lines.append("Flexible constraints:")
        for key, item in self.flexible_items():
            weight = f"weight={item.weight}" if item.mode == ConstraintMode.SOFT else ""
            lines.append(f"  {key:<32} {item.mode.value:<5} {weight}".rstrip())

        lines.append("Soft constraints:")
        for key, item in self.soft_items():
            label = SOFT_CONSTRAINT_IDS.get(key, "")
            if item.enabled:
                lines.append(f"  {key:<32} on    weight={item.weight} {label}".rstrip())
            else:
                lines.append(f"  {key:<32} off".rstrip())
        return lines


class TimetableConfigError(ValueError):
    """Raised when a timetable configuration file is missing or invalid."""


def parse_timetable_config(data: dict) -> TimetableConfig:
    try:
        return TimetableConfig.model_validate(data)
    except ValueError as exc:
        raise TimetableConfigError(f"Invalid timetable configuration:\n{exc}") from exc


def load_timetable_config(path: str | Path | None = None) -> TimetableConfig:
    """Load and validate a timetable configuration file.

    ``path=None`` loads ``config/timetable.toml`` when it exists and falls
    back to built-in defaults otherwise. An explicit path must exist.
    """

    if path is None:
        if not DEFAULT_CONFIG_PATH.exists():
            return TimetableConfig()
        path = DEFAULT_CONFIG_PATH

    path = Path(path)

    if not path.exists():
        raise TimetableConfigError(f"Timetable configuration file not found: {path}")

    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise TimetableConfigError(f"Invalid TOML in {path}: {exc}") from exc

    return parse_timetable_config(data)


# ---------------------------------------------------------------------------
# Writing (used by the web UI's config editor)
# ---------------------------------------------------------------------------


def _toml_value(value: object) -> str:
    if value is None:
        return f'"{NONE_SENTINEL}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise TypeError(f"Cannot write {type(value).__name__} to TOML")


def _is_table_array(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, dict) for item in value)


def _write_table(lines: list[str], path: list[str], table: dict) -> None:
    scalars = {
        key: value
        for key, value in table.items()
        if not isinstance(value, dict) and not _is_table_array(value)
    }
    if path and (scalars or not table):
        lines.append("")
        lines.append(f"[{'.'.join(path)}]")
    for key, value in scalars.items():
        lines.append(f"{key} = {_toml_value(value)}")
    for key, value in table.items():
        if isinstance(value, dict):
            _write_table(lines, [*path, key], value)
        elif _is_table_array(value):
            for item in value:
                lines.append("")
                lines.append(f"[[{'.'.join([*path, key])}]]")
                for item_key, item_value in item.items():
                    lines.append(f"{item_key} = {_toml_value(item_value)}")


def dump_timetable_config(config: TimetableConfig) -> str:
    """Serialise a config to TOML that :func:`load_timetable_config` reads back."""

    lines = [
        "# Open Timetable Generator - constraint and solver configuration.",
        "# Edited from the web UI (Constraints page) or by hand. Unknown keys are rejected.",
        f'# "{NONE_SENTINEL}" means "not set" for optional values.',
    ]
    _write_table(lines, [], config.model_dump(mode="json"))
    return "\n".join(lines) + "\n"


class ConfigStore:
    """Read/write access to one TOML config file, reloaded when it changes."""

    def __init__(self, path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        self.path = Path(path)
        self._cached: tuple[float, TimetableConfig] | None = None

    def load(self) -> TimetableConfig:
        if not self.path.exists():
            return TimetableConfig()
        mtime = self.path.stat().st_mtime
        if self._cached is None or self._cached[0] != mtime:
            self._cached = (mtime, load_timetable_config(self.path))
        return self._cached[1]

    def save(self, config: TimetableConfig) -> TimetableConfig:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".toml.tmp")
        temporary.write_text(dump_timetable_config(config), encoding="utf-8")
        temporary.replace(self.path)
        self._cached = None
        return self.load()

    def reset(self) -> TimetableConfig:
        return self.save(TimetableConfig())
