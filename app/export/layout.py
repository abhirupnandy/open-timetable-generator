"""Layout helpers shared by the Excel and PDF exports.

Both exports show the same things: one days x periods grid per group,
faculty member or room, and tables of sessions and faculty load. This
module decides *what* goes where (which sessions belong to an entity,
which periods merge into one cell, how loads are counted); the exporters
only decide how it looks.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from app.domain.calendar import Day
from app.domain.timetable_views import TimetableViewEntry, faculty_label

VIEWS = ("group", "faculty", "room")

DAY_ORDER = {day.value: index for index, day in enumerate(Day)}


@dataclass(frozen=True)
class ExportCalendar:
    """Days, periods and their clock times as shown in exports."""

    days: tuple[str, ...]
    periods_per_day: int
    period_times: Mapping[int, tuple[str, str]] = field(default_factory=dict)
    lunch_after_period: int | None = None
    blocked: Mapping[tuple[str, int], str] = field(default_factory=dict)
    # Group-specific blocks: (group code, day, period, label).
    group_blocked: tuple[tuple[str, str, int, str], ...] = ()

    @property
    def periods(self) -> range:
        return range(1, self.periods_per_day + 1)

    def period_header(self, period: int) -> str:
        times = self.period_times.get(period)
        return f"P{period}\n{times[0]}–{times[1]}" if times else f"P{period}"

    def time_range(self, start_period: int, end_period: int) -> str:
        """Clock range of a session, e.g. "08:20–10:20" (or "P1–P2" without times)."""

        start = self.period_times.get(start_period)
        end = self.period_times.get(end_period)
        if start and end:
            return f"{start[0]}–{end[1]}"
        return period_range(start_period, end_period)

    def for_entity(
        self,
        by: str,
        key: str,
        group_parents: Mapping[str, str | None] | None = None,
    ) -> ExportCalendar:
        """Calendar of one grid: global blocks plus, for a group, the blocks of
        every group whose students overlap with it (ancestors and batches),
        exactly as the solver applies them. A block from another group is
        labelled with that group's code."""

        if by != "group" or not self.group_blocked:
            return self
        related = related_codes(key, group_parents or {})
        blocked = dict(self.blocked)
        for code, day, period, label in self.group_blocked:
            if code not in related or (day, period) in blocked:
                continue
            text = label or "Blocked"
            blocked[(day, period)] = text if code == key else f"{text} ({code})"
        return replace(self, blocked=blocked)

    @classmethod
    def plain(cls, days: Iterable[str], periods_per_day: int) -> ExportCalendar:
        return cls(days=tuple(days), periods_per_day=periods_per_day)


def period_range(start_period: int, end_period: int) -> str:
    return f"P{start_period}" if start_period == end_period else f"P{start_period}–P{end_period}"


def day_title(day: str) -> str:
    return day.title()


def entry_sort_key(entry: TimetableViewEntry) -> tuple:
    return (
        DAY_ORDER.get(entry.day.value, 99),
        entry.start_period,
        entry.course_code,
        entry.academic_group_code,
        entry.session_id,
    )


# ---------------------------------------------------------------------------
# Entities (one grid each)
# ---------------------------------------------------------------------------


def related_codes(code: str, parents: Mapping[str, str | None]) -> set[str]:
    """Codes whose students overlap with ``code``: itself, ancestors and descendants."""

    related = {code}
    current = parents.get(code)

    while current is not None and current not in related:
        related.add(current)
        current = parents.get(current)

    for other in parents:
        ancestor = parents.get(other)
        seen: set[str] = set()
        while ancestor is not None and ancestor not in seen:
            if ancestor == code:
                related.add(other)
                break
            seen.add(ancestor)
            ancestor = parents.get(ancestor)

    return related


@dataclass(frozen=True)
class Entity:
    key: str
    title: str
    subtitle: str = ""


def entities(
    entries: Sequence[TimetableViewEntry],
    by: str,
    group_parents: Mapping[str, str | None] | None = None,
) -> list[Entity]:
    """Every group, faculty member or room that has a timetable, sorted."""

    if by == "group":
        names = {entry.academic_group_code: entry.academic_group_name for entry in entries}
        codes = sorted(set(names) | set(group_parents or {}))
        return [Entity(code, code, names.get(code, "")) for code in codes]

    if by == "faculty":
        found: dict[str, TimetableViewEntry] = {}
        for entry in entries:
            found.setdefault(entry.faculty_key, entry)
        return sorted(
            (
                Entity(
                    key,
                    faculty_label(entry.faculty_name, entry.faculty_designation),
                    entry.faculty_code,
                )
                for key, entry in found.items()
            ),
            key=lambda item: (item.title.casefold(), item.key),
        )

    if by == "room":
        rooms = sorted({entry.room_name for entry in entries if entry.room_name is not None})
        return [Entity(room, room) for room in rooms]

    raise ValueError(f"Unsupported view: {by!r}")


def entries_for(
    entries: Sequence[TimetableViewEntry],
    by: str,
    key: str,
    group_parents: Mapping[str, str | None] | None = None,
) -> list[TimetableViewEntry]:
    if by == "group":
        related = related_codes(key, group_parents or {})
        selected = [entry for entry in entries if entry.academic_group_code in related]
    elif by == "faculty":
        selected = [entry for entry in entries if entry.faculty_key == key]
    elif by == "room":
        selected = [entry for entry in entries if entry.room_name == key]
    else:
        raise ValueError(f"Unsupported view: {by!r}")
    return sorted(selected, key=entry_sort_key)


# ---------------------------------------------------------------------------
# Grid cells
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GridCell:
    """One cell of a day row: sessions spanning ``span`` periods, or a block."""

    period: int
    span: int
    entries: tuple[TimetableViewEntry, ...] = ()
    blocked_label: str | None = None


def _covering(entries: Sequence[TimetableViewEntry], day: str, period: int):
    return tuple(
        entry
        for entry in entries
        if entry.day.value == day and entry.start_period <= period <= entry.end_period
    )


def day_cells(
    entries: Sequence[TimetableViewEntry],
    day: str,
    calendar: ExportCalendar,
) -> list[GridCell]:
    """Cells for one day. Consecutive periods holding the same sessions merge
    (a two-period lab becomes one cell) unless lunch falls between them."""

    cells: list[GridCell] = []
    periods = list(calendar.periods)
    lunch = calendar.lunch_after_period
    index = 0

    while index < len(periods):
        period = periods[index]
        here = _covering(entries, day, period)
        ids = sorted(entry.session_id for entry in here)
        span = 1

        if here:
            while index + span < len(periods) and period + span - 1 != lunch:
                following = _covering(entries, day, period + span)
                if sorted(entry.session_id for entry in following) != ids:
                    break
                span += 1

        label = calendar.blocked.get((day, period))
        if not here and label is not None:
            cells.append(GridCell(period, 1, blocked_label=label or "Blocked"))
        else:
            cells.append(GridCell(period, span, here))
        index += span

    return cells


def cell_lines(entry: TimetableViewEntry, by: str) -> tuple[str, list[str]]:
    """Title and detail lines describing a session inside a grid cell."""

    details = []
    if by != "group":
        details.append(entry.academic_group_code)
    if by != "faculty":
        details.append(entry.faculty_label)
    if by != "room":
        details.append(entry.room_name or "Online")
    return entry.subject_name, details


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


def busy_periods_by_day(entries: Iterable[TimetableViewEntry]) -> dict[str, int]:
    """Distinct occupied periods per day (parallel batches count once)."""

    busy: dict[str, set[int]] = defaultdict(set)
    for entry in entries:
        busy[entry.day.value].update(range(entry.start_period, entry.end_period + 1))
    return {day: len(periods) for day, periods in busy.items()}


@dataclass(frozen=True)
class FacultyLoad:
    employee_id: str
    name: str
    designation: str
    sessions: int
    per_day: dict[str, int]

    @property
    def weekly(self) -> int:
        return sum(self.per_day.values())

    @property
    def busiest_day(self) -> int:
        return max(self.per_day.values(), default=0)


def faculty_loads(entries: Sequence[TimetableViewEntry]) -> list[FacultyLoad]:
    """Teaching periods per day and per week for every faculty member."""

    grouped: dict[str, list[TimetableViewEntry]] = defaultdict(list)
    for entry in entries:
        grouped[entry.faculty_key].append(entry)

    loads = [
        FacultyLoad(
            employee_id=items[0].faculty_code,
            name=items[0].faculty_name,
            designation=items[0].faculty_designation,
            sessions=len(items),
            per_day=busy_periods_by_day(items),
        )
        for items in grouped.values()
    ]
    return sorted(loads, key=lambda load: (load.name.casefold(), load.employee_id))


# ---------------------------------------------------------------------------
# Run results stored as JSON (``timetable_runs.result_json``)
# ---------------------------------------------------------------------------


def entries_from_payload(rows: Iterable[Mapping]) -> tuple[TimetableViewEntry, ...]:
    return tuple(
        TimetableViewEntry(
            session_id=row["session_id"],
            day=Day(row["day"]),
            start_period=row["start_period"],
            end_period=row["end_period"],
            subject_name=row["subject"],
            course_code=row.get("course_code", ""),
            course_name=row.get("course_name", ""),
            academic_group_name=row.get("group_name", ""),
            academic_group_code=row["group_code"],
            faculty_name=row["faculty"],
            room_name=row.get("room"),
            faculty_code=row.get("faculty_code") or "",
            faculty_designation=row.get("faculty_designation") or "",
        )
        for row in rows
    )


def calendar_from_payload(calendar: Mapping) -> ExportCalendar:
    periods = calendar.get("periods", [])
    return ExportCalendar(
        days=tuple(calendar.get("days", ())),
        periods_per_day=len(periods),
        period_times={
            item["number"]: (item["start"], item["end"])
            for item in periods
            if item.get("start") and item.get("end")
        },
        lunch_after_period=calendar.get("lunch_after_period"),
        blocked={
            (item["day"], item["period"]): item.get("label", "")
            for item in calendar.get("blocked_slots", [])
        },
        group_blocked=tuple(
            (item["group_code"], item["day"], item["period"], item.get("label", ""))
            for item in calendar.get("group_blocked_slots", [])
        ),
    )


def group_block_rows(timetable_input, group_codes: Mapping[int, str], enabled: bool) -> list[dict]:
    """Group blocked slots of a ``TimetableInput`` keyed by group code.

    Empty when the ``group_blocked_slots`` hard constraint is disabled, since
    the solver then ignores them.
    """

    if not enabled:
        return []
    return [
        {
            "group_code": group_codes[block.academic_group_id],
            "day": block.day.value,
            "period": block.period,
            "label": block.label,
        }
        for block in timetable_input.group_blocked_slots or ()
        if block.academic_group_id in group_codes
    ]


def calendar_from_input(
    timetable_input,
    blocked_slots: Iterable = (),
    group_blocked: Iterable[Mapping] = (),
) -> ExportCalendar:
    """Export calendar of a ``TimetableInput`` (``blocked_slots``: config
    entries; ``group_blocked``: rows from ``group_block_rows``)."""

    def hhmm(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    times = timetable_input.period_times or {}
    return ExportCalendar(
        days=tuple(day.value for day in timetable_input.days),
        periods_per_day=timetable_input.periods_per_day,
        period_times={number: (hhmm(start), hhmm(end)) for number, (start, end) in times.items()},
        lunch_after_period=timetable_input.lunch_after_period,
        blocked={(str(slot.day), slot.period): slot.label for slot in blocked_slots},
        group_blocked=tuple(
            (row["group_code"], row["day"], row["period"], row["label"]) for row in group_blocked
        ),
    )
