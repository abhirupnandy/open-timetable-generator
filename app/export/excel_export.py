"""Excel exports of a finished timetable.

Two kinds of sheet:

* **Lists**: one row per session with the day, clock time, subject,
  group, faculty (with designation) and room. Internal session IDs are
  left out; they are only in the CSV, which is read back by
  ``stability_vs_previous``.
* **Grids**: days x periods, the format people print. Multi-period
  sessions are merged into one cell, each subject has its own colour, and
  every row ends with the number of periods taught / attended that day.

Faculty load (teaching periods per day and per week) appears as a
"Faculty load" sheet in the master and by-faculty workbooks and as the
"Load" column of every faculty grid.
"""

from __future__ import annotations

import zlib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.domain.timetable_views import TimetableViewEntry, designation_label
from app.export.layout import (
    DAY_ORDER,
    ExportCalendar,
    cell_lines,
    day_cells,
    day_title,
    entities,
    entries_for,
    entry_sort_key,
    faculty_loads,
    period_range,
)

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

NAVY = "1F4E78"
HEADER_FILL = PatternFill(fill_type="solid", fgColor=NAVY)
HEADER_FONT = Font(bold=True, color="FFFFFF")
TITLE_FONT = Font(bold=True, size=14, color=NAVY)
SUBTITLE_FONT = Font(italic=True, color="595959")
BAND_FILL = PatternFill(fill_type="solid", fgColor="F2F6FA")
DAY_FILL = PatternFill(fill_type="solid", fgColor="DDE7F0")
LUNCH_FILL = PatternFill(fill_type="solid", fgColor="EDEDED")
BLOCKED_FILL = PatternFill(fill_type="lightUp", fgColor="BFBFBF", bgColor="F7F7F7")
TOTAL_FILL = PatternFill(fill_type="solid", fgColor="FFF2CC")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP_TOP = Alignment(vertical="top", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Light pastel fills; one per subject, chosen by a stable hash of its name.
SUBJECT_FILLS = (
    "DCEBFA",
    "E2F0D9",
    "FCE4D6",
    "EDE2F6",
    "FFF2CC",
    "D9F2F2",
    "F8DCE6",
    "E7E6E6",
    "DDEBF7",
    "E2EFDA",
    "FBE5D6",
    "E4DFEC",
)
BOLD = InlineFont(b=True)
MUTED = InlineFont(color="595959", sz=9)

# List columns: (header, width, value(entry, calendar)).
LIST_COLUMNS = {
    "day": ("Day", 12, lambda e, c: day_title(e.day.value)),
    "time": ("Time", 14, lambda e, c: c.time_range(e.start_period, e.end_period)),
    "periods": ("Periods", 10, lambda e, c: period_range(e.start_period, e.end_period)),
    "subject": ("Subject", 34, lambda e, c: e.subject_name),
    "course": ("Course", 14, lambda e, c: e.course_code),
    "group": ("Group", 22, lambda e, c: e.academic_group_code),
    "faculty": ("Faculty", 26, lambda e, c: e.faculty_name),
    "designation": (
        "Designation",
        14,
        lambda e, c: designation_label(e.faculty_designation) if e.faculty_designation else "",
    ),
    "room": ("Room", 12, lambda e, c: e.room_name or "Online"),
}
ALL_LIST_COLUMNS = tuple(LIST_COLUMNS)


def _subject_fill(subject: str) -> PatternFill:
    colour = SUBJECT_FILLS[zlib.crc32(subject.encode()) % len(SUBJECT_FILLS)]
    return PatternFill(fill_type="solid", fgColor=colour)


# ---------------------------------------------------------------------------
# Workbook helpers
# ---------------------------------------------------------------------------


def _safe_sheet_name(name: str, fallback: str) -> str:
    """Return a valid Excel worksheet name (max 31 chars, no []:*?/\\)."""

    cleaned = name
    for character, replacement in {
        "/": "-",
        "\\": "-",
        "*": "-",
        "?": "-",
        ":": "-",
        "[": "(",
        "]": ")",
    }.items():
        cleaned = cleaned.replace(character, replacement)
    return (cleaned.strip() or fallback)[:31]


def _unique_sheet_name(workbook: Workbook, name: str, fallback: str) -> str:
    base = _safe_sheet_name(name, fallback)
    candidate = base
    counter = 2
    while candidate in workbook.sheetnames:
        suffix = f" ({counter})"
        candidate = base[: 31 - len(suffix)] + suffix
        counter += 1
    return candidate


def _create_workbook() -> Workbook:
    workbook = Workbook()
    workbook.remove(workbook.active)
    return workbook


def _save(workbook: Workbook, output_path: Path) -> Path:
    """Save, adding a placeholder sheet if there is none (openpyxl needs one)."""

    if not workbook.worksheets:
        worksheet = workbook.create_sheet("No sessions")
        worksheet.append(["No sessions to display."])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return output_path


def _calendar(
    calendar: ExportCalendar | None,
    entries: Sequence[TimetableViewEntry],
    days: Iterable[str] | None = None,
    periods_per_day: int | None = None,
) -> ExportCalendar:
    if calendar is not None:
        return calendar
    if days is None:
        days = sorted({entry.day.value for entry in entries}, key=lambda d: DAY_ORDER.get(d, 99))
    if periods_per_day is None:
        periods_per_day = max((entry.end_period for entry in entries), default=1)
    return ExportCalendar.plain(days, periods_per_day)


def _write_title(worksheet, title: str, subtitle: str, width: int) -> int:
    """Write a title (and optional subtitle) above a table; returns the next row."""

    worksheet.cell(1, 1, title).font = TITLE_FONT
    worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(width, 1))
    worksheet.row_dimensions[1].height = 22
    row = 2
    if subtitle:
        worksheet.cell(2, 1, subtitle).font = SUBTITLE_FONT
        worksheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(width, 1))
        row = 3
    return row + 1  # blank spacer row


def _write_header(worksheet, row: int, headers: Sequence[str]) -> None:
    for column, header in enumerate(headers, start=1):
        cell = worksheet.cell(row, column, header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER
        cell.border = BORDER


def _page_setup(worksheet, *, title_rows: str | None = None, one_page: bool = False) -> None:
    worksheet.page_setup.orientation = "landscape"
    worksheet.page_setup.paperSize = worksheet.PAPERSIZE_A4
    worksheet.page_setup.fitToWidth = 1
    worksheet.page_setup.fitToHeight = 1 if one_page else 0
    worksheet.sheet_properties.pageSetUpPr.fitToPage = True
    worksheet.print_options.horizontalCentered = True
    worksheet.page_margins.left = worksheet.page_margins.right = 0.4
    if title_rows:
        worksheet.print_title_rows = title_rows


# ---------------------------------------------------------------------------
# List sheets
# ---------------------------------------------------------------------------


def _write_list(
    worksheet,
    entries: Sequence[TimetableViewEntry],
    calendar: ExportCalendar,
    *,
    title: str,
    subtitle: str = "",
    columns: Sequence[str] = ALL_LIST_COLUMNS,
) -> None:
    """A readable list of sessions, banded by day."""

    specs = [LIST_COLUMNS[name] for name in columns]
    header_row = _write_title(worksheet, title, subtitle, len(specs))
    _write_header(worksheet, header_row, [spec[0] for spec in specs])

    band = False
    previous_day = None
    row = header_row
    for entry in entries:
        row += 1
        if entry.day != previous_day:
            band = not band
            previous_day = entry.day
        for column, (_, _, value) in enumerate(specs, start=1):
            cell = worksheet.cell(row, column, value(entry, calendar))
            cell.border = BORDER
            cell.alignment = WRAP_TOP
            if band:
                cell.fill = BAND_FILL

    if not entries:
        worksheet.cell(header_row + 1, 1, "No sessions.").font = SUBTITLE_FONT

    for column, (_, width, _) in enumerate(specs, start=1):
        worksheet.column_dimensions[get_column_letter(column)].width = width

    worksheet.freeze_panes = worksheet.cell(header_row + 1, 1)
    if entries:
        last = get_column_letter(len(specs))
        worksheet.auto_filter.ref = f"A{header_row}:{last}{row}"
    _page_setup(worksheet, title_rows=f"{header_row}:{header_row}")


def _write_summary_sheet(worksheet, rows: Iterable[list]) -> None:
    for row in rows:
        worksheet.append(list(row))

    for cell in worksheet["A"]:
        cell.font = Font(bold=True)

    for column, width in {
        "A": 32,
        "B": 14,
        "C": 8,
        "D": 8,
        "E": 8,
        "F": 10,
        "G": 8,
        "H": 10,
    }.items():
        worksheet.column_dimensions[column].width = width

    _page_setup(worksheet)
    worksheet.page_setup.orientation = "portrait"


def _write_load_sheet(
    worksheet,
    entries: Sequence[TimetableViewEntry],
    calendar: ExportCalendar,
) -> None:
    """Teaching periods per day and per week for every faculty member."""

    days = list(calendar.days)
    headers = [
        "Employee ID",
        "Faculty",
        "Designation",
        *(day_title(day)[:3] for day in days),
        "Weekly load",
        "Busiest day",
        "Sessions",
    ]
    header_row = _write_title(
        worksheet,
        "Faculty load",
        "Teaching periods per day and per week (parallel sessions count once).",
        len(headers),
    )
    _write_header(worksheet, header_row, headers)

    loads = faculty_loads(entries)
    row = header_row
    for index, load in enumerate(loads):
        row += 1
        values = [
            load.employee_id,
            load.name,
            designation_label(load.designation) if load.designation else "",
            *(load.per_day.get(day, 0) for day in days),
            load.weekly,
            load.busiest_day,
            load.sessions,
        ]
        for column, value in enumerate(values, start=1):
            cell = worksheet.cell(row, column, value)
            cell.border = BORDER
            if column > 3:
                cell.alignment = Alignment(horizontal="center")
            if index % 2:
                cell.fill = BAND_FILL
        worksheet.cell(row, 4 + len(days)).font = Font(bold=True)

    if loads:
        row += 1
        worksheet.cell(row, 2, "Total").font = Font(bold=True)
        first, last = header_row + 1, row - 1
        for column in range(4, len(headers) + 1):
            letter = get_column_letter(column)
            function = "MAX" if headers[column - 1] == "Busiest day" else "SUM"
            cell = worksheet.cell(row, column, f"={function}({letter}{first}:{letter}{last})")
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")
        for column in range(1, len(headers) + 1):
            worksheet.cell(row, column).fill = TOTAL_FILL
            worksheet.cell(row, column).border = BORDER

    for column, width in enumerate([14, 28, 14, *([7] * len(days)), 12, 12, 10], start=1):
        worksheet.column_dimensions[get_column_letter(column)].width = width
    worksheet.freeze_panes = worksheet.cell(header_row + 1, 3)
    _page_setup(worksheet, title_rows=f"{header_row}:{header_row}")


# ---------------------------------------------------------------------------
# Public list exports
# ---------------------------------------------------------------------------


def export_master_workbook(
    entries: tuple[TimetableViewEntry, ...],
    output_path: str | Path,
    *,
    summary_rows: Iterable[list] | None = None,
    calendar: ExportCalendar | None = None,
) -> Path:
    """All sessions in one sheet, plus "Summary" (score report) and "Faculty load"."""

    calendar = _calendar(calendar, entries)
    workbook = _create_workbook()

    if summary_rows is not None:
        _write_summary_sheet(workbook.create_sheet("Summary"), summary_rows)

    _write_list(
        workbook.create_sheet("Timetable"),
        sorted(entries, key=entry_sort_key),
        calendar,
        title="Timetable: all sessions",
        subtitle=f"{len(entries)} sessions. Use the filter buttons in the header row.",
    )
    _write_load_sheet(workbook.create_sheet("Faculty load"), entries, calendar)
    return _save(workbook, Path(output_path))


def export_day_workbook(
    entries: tuple[TimetableViewEntry, ...],
    output_path: str | Path,
    *,
    calendar: ExportCalendar | None = None,
) -> Path:
    """One sheet per day."""

    calendar = _calendar(calendar, entries, days=[day for day in DAY_ORDER])
    workbook = _create_workbook()

    by_day: dict[str, list[TimetableViewEntry]] = defaultdict(list)
    for entry in entries:
        by_day[entry.day.value].append(entry)

    for day in calendar.days:
        day_entries = sorted(by_day.get(day, []), key=entry_sort_key)
        _write_list(
            workbook.create_sheet(_safe_sheet_name(day_title(day), day_title(day))),
            day_entries,
            calendar,
            title=f"{day_title(day)}",
            subtitle=f"{len(day_entries)} sessions",
            columns=[name for name in ALL_LIST_COLUMNS if name != "day"],
        )

    return _save(workbook, Path(output_path))


def export_faculty_workbook(
    entries: tuple[TimetableViewEntry, ...],
    output_path: str | Path,
    *,
    calendar: ExportCalendar | None = None,
) -> Path:
    """A "Faculty load" overview, then one sheet per faculty member."""

    calendar = _calendar(calendar, entries)
    workbook = _create_workbook()

    if entries:
        _write_load_sheet(workbook.create_sheet("Faculty load"), entries, calendar)

    for entity in entities(entries, "faculty"):
        selected = entries_for(entries, "faculty", entity.key)
        periods = sum(entry.end_period - entry.start_period + 1 for entry in selected)
        _write_list(
            workbook.create_sheet(_unique_sheet_name(workbook, entity.title, "Faculty")),
            selected,
            calendar,
            title=entity.title,
            subtitle=" · ".join(
                part
                for part in (entity.subtitle, f"{len(selected)} sessions, {periods} periods/week")
                if part
            ),
            columns=[name for name in ALL_LIST_COLUMNS if name not in {"faculty", "designation"}],
        )

    return _save(workbook, Path(output_path))


# ---------------------------------------------------------------------------
# Grid exports (days x periods), the format people print
# ---------------------------------------------------------------------------


def _rich_cell(entries: Sequence[TimetableViewEntry], by: str) -> tuple[CellRichText | str, int]:
    """Cell content (subject in bold, details below) and its number of lines."""

    parts: list = []
    lines = 0
    for index, entry in enumerate(entries):
        title, details = cell_lines(entry, by)
        if index:
            parts.append("\n\n")
            lines += 1
        parts.append(TextBlock(BOLD, title))
        lines += 1
        for detail in details:
            parts.append(TextBlock(MUTED, f"\n{detail}"))
            lines += 1
    if not parts:
        return "", 0
    return CellRichText(*parts), lines


def _write_grid(
    worksheet,
    entries: Sequence[TimetableViewEntry],
    calendar: ExportCalendar,
    *,
    by: str,
    title: str,
    subtitle: str,
) -> None:
    periods = list(calendar.periods)
    lunch = calendar.lunch_after_period

    # Column of every period (a narrow lunch column follows ``lunch``).
    column_of: dict[int, int] = {}
    column = 2
    lunch_column = None
    for period in periods:
        column_of[period] = column
        column += 1
        if period == lunch:
            lunch_column = column
            column += 1
    load_column = column

    header_row = _write_title(worksheet, title, subtitle, load_column)
    headers = ["Day"] + [""] * (load_column - 1)
    for period in periods:
        headers[column_of[period] - 1] = calendar.period_header(period)
    if lunch_column:
        headers[lunch_column - 1] = "Lunch"
    headers[load_column - 1] = "Load\n(periods)"
    _write_header(worksheet, header_row, headers)
    worksheet.row_dimensions[header_row].height = 30

    by_day: dict[str, list[TimetableViewEntry]] = defaultdict(list)
    for entry in entries:
        by_day[entry.day.value].append(entry)

    weekly = 0
    row = header_row
    for day in calendar.days:
        row += 1
        day_cell = worksheet.cell(row, 1, day_title(day))
        day_cell.font = Font(bold=True)
        day_cell.fill = DAY_FILL
        day_cell.alignment = CENTER
        day_cell.border = BORDER

        max_lines = 1
        busy: set[int] = set()
        for cell in day_cells(by_day.get(day, []), day, calendar):
            start = column_of[cell.period]
            end = column_of[cell.period + cell.span - 1]
            target = worksheet.cell(row, start)
            if cell.blocked_label is not None:
                target.value = cell.blocked_label
                target.fill = BLOCKED_FILL
                target.alignment = CENTER
                target.font = Font(italic=True, color="595959")
            elif cell.entries:
                target.value, lines = _rich_cell(cell.entries, by)
                max_lines = max(max_lines, lines)
                target.fill = _subject_fill(cell.entries[0].subject_name)
                target.alignment = WRAP_TOP
                busy.update(range(cell.period, cell.period + cell.span))
            for col in range(start, end + 1):
                worksheet.cell(row, col).border = BORDER
            if end > start:
                worksheet.merge_cells(
                    start_row=row, start_column=start, end_row=row, end_column=end
                )

        if lunch_column:
            lunch_cell = worksheet.cell(row, lunch_column)
            lunch_cell.fill = LUNCH_FILL
            lunch_cell.border = BORDER

        load_cell = worksheet.cell(row, load_column, len(busy))
        load_cell.font = Font(bold=True)
        load_cell.alignment = CENTER
        load_cell.fill = TOTAL_FILL
        load_cell.border = BORDER
        weekly += len(busy)
        worksheet.row_dimensions[row].height = max(30, 13 * max_lines + 4)

    row += 1
    label = worksheet.cell(row, load_column - 1, "Weekly load")
    label.font = Font(bold=True)
    label.alignment = Alignment(horizontal="right", vertical="center")
    total = worksheet.cell(row, load_column, weekly)
    total.font = Font(bold=True)
    total.alignment = CENTER
    total.fill = TOTAL_FILL
    total.border = BORDER

    worksheet.column_dimensions["A"].width = 12
    for period in periods:
        worksheet.column_dimensions[get_column_letter(column_of[period])].width = 22
    if lunch_column:
        worksheet.column_dimensions[get_column_letter(lunch_column)].width = 7
    worksheet.column_dimensions[get_column_letter(load_column)].width = 10
    worksheet.freeze_panes = worksheet.cell(header_row + 1, 2)
    _page_setup(worksheet, one_page=True)


def export_grid_workbook(
    entries: tuple[TimetableViewEntry, ...],
    output_path: str | Path,
    *,
    by: str,
    days: Iterable[str] | None = None,
    periods_per_day: int | None = None,
    group_parents: Mapping[str, str | None] | None = None,
    calendar: ExportCalendar | None = None,
) -> Path:
    """One days x periods grid per group, faculty member or room.

    For groups, ``group_parents`` (code -> parent code) makes each sheet
    also show the sessions of ancestor and descendant groups, i.e.
    everything the students of that group attend.
    """

    if by not in {"group", "faculty", "room"}:
        raise ValueError(f"Unsupported grid export: {by!r}")

    calendar = _calendar(calendar, entries, days, periods_per_day)
    workbook = _create_workbook()

    for entity in entities(entries, by, group_parents):
        selected = entries_for(entries, by, entity.key, group_parents)
        if not selected:
            continue
        sessions = len(selected)
        subtitle = " · ".join(part for part in (entity.subtitle, f"{sessions} sessions") if part)
        _write_grid(
            workbook.create_sheet(_unique_sheet_name(workbook, entity.title, by.title())),
            selected,
            calendar.for_entity(by, entity.key, group_parents),
            by=by,
            title=f"{by.title()}: {entity.title}",
            subtitle=subtitle,
        )

    return _save(workbook, Path(output_path))


def export_all(
    entries: tuple[TimetableViewEntry, ...],
    output_dir: str | Path,
    *,
    calendar: ExportCalendar,
    group_parents: Mapping[str, str | None],
    summary_rows: Iterable[list] | None = None,
) -> dict[str, Path]:
    """Write every Excel export of a run; returns {file name: path}."""

    output_dir = Path(output_dir)
    written = {
        "timetable_master.xlsx": export_master_workbook(
            entries,
            output_dir / "timetable_master.xlsx",
            summary_rows=summary_rows,
            calendar=calendar,
        ),
        "timetable_by_day.xlsx": export_day_workbook(
            entries, output_dir / "timetable_by_day.xlsx", calendar=calendar
        ),
        "timetable_by_faculty.xlsx": export_faculty_workbook(
            entries, output_dir / "timetable_by_faculty.xlsx", calendar=calendar
        ),
    }
    for by in ("group", "faculty", "room"):
        name = f"grid_by_{by}.xlsx"
        written[name] = export_grid_workbook(
            entries,
            output_dir / name,
            by=by,
            group_parents=group_parents,
            calendar=calendar,
        )
    return written
