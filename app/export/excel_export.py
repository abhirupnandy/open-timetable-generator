from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.domain.timetable_views import TimetableViewEntry

_HEADERS = [
    "Session ID",
    "Day",
    "Start Period",
    "End Period",
    "Duration",
    "Subject",
    "Course Code",
    "Course Name",
    "Academic Group Code",
    "Academic Group Name",
    "Faculty",
    "Room",
]


_DAY_ORDER = {
    "MONDAY": 0,
    "TUESDAY": 1,
    "WEDNESDAY": 2,
    "THURSDAY": 3,
    "FRIDAY": 4,
    "SATURDAY": 5,
}


def _entry_sort_key(entry: TimetableViewEntry) -> tuple:
    return (
        _DAY_ORDER.get(entry.day.value, 99),
        entry.start_period,
        entry.course_code,
        entry.academic_group_code,
        entry.session_id,
    )


def _safe_sheet_name(name: str, fallback: str) -> str:
    """Return a valid and reasonably unique Excel worksheet name."""

    invalid_characters = {
        "/": "-",
        "\\": "-",
        "*": "-",
        "?": "-",
        ":": "-",
        "[": "(",
        "]": ")",
    }

    cleaned = name

    for character, replacement in invalid_characters.items():
        cleaned = cleaned.replace(character, replacement)

    cleaned = cleaned.strip() or fallback

    # Excel worksheet names are limited to 31 characters.
    return cleaned[:31]


def _write_sheet(
    worksheet,
    entries: tuple[TimetableViewEntry, ...],
) -> None:
    """Write timetable entries to one worksheet."""

    worksheet.append(_HEADERS)

    for cell in worksheet[1]:
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78",
        )
        cell.font = Font(
            bold=True,
            color="FFFFFF",
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for entry in entries:
        duration = (
            entry.end_period
            - entry.start_period
            + 1
        )

        worksheet.append(
            [
                entry.session_id,
                entry.day.value,
                entry.start_period,
                entry.end_period,
                duration,
                entry.subject_name,
                entry.course_code,
                entry.course_name,
                entry.academic_group_code,
                entry.academic_group_name,
                entry.faculty_name,
                entry.room_name or "ONLINE",
            ]
        )

    worksheet.freeze_panes = "A2"

    if worksheet.max_row >= 2:
        worksheet.auto_filter.ref = worksheet.dimensions

    widths = {
        "A": 28,
        "B": 14,
        "C": 14,
        "D": 14,
        "E": 12,
        "F": 32,
        "G": 18,
        "H": 34,
        "I": 28,
        "J": 45,
        "K": 25,
        "L": 15,
    }

    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width

    for row in worksheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

    worksheet.page_setup.orientation = "landscape"
    worksheet.page_setup.fitToWidth = 1
    worksheet.page_setup.fitToHeight = 0
    worksheet.sheet_properties.pageSetUpPr.fitToPage = True
    worksheet.print_title_rows = "1:1"


def _create_workbook() -> Workbook:
    """Create a workbook with the default worksheet removed."""

    workbook = Workbook()

    default_sheet = workbook.active
    workbook.remove(default_sheet)

    return workbook


def _save(workbook: Workbook, output_path: Path) -> Path:
    """Save a workbook, adding a placeholder sheet if it would have none.

    openpyxl refuses to save a workbook without a visible sheet
    ("At least one sheet must be visible").
    """

    if not workbook.worksheets:
        worksheet = workbook.create_sheet("No sessions")
        worksheet.append(["No sessions to display."])

    workbook.save(output_path)
    return output_path


def _write_summary_sheet(worksheet, rows: Iterable[list]) -> None:
    for row in rows:
        worksheet.append(list(row))

    for cell in worksheet["A"]:
        cell.font = Font(bold=True)

    widths = {"A": 32, "B": 14, "C": 8, "D": 8, "E": 8, "F": 10, "G": 8, "H": 10}

    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width


def export_master_workbook(
    entries: tuple[TimetableViewEntry, ...],
    output_path: str | Path,
    *,
    summary_rows: Iterable[list] | None = None,
) -> Path:
    """Export all timetable entries to one master workbook.

    ``summary_rows`` (from the score report) adds a "Summary" sheet.
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = _create_workbook()

    if summary_rows is not None:
        _write_summary_sheet(workbook.create_sheet("Summary"), summary_rows)

    worksheet = workbook.create_sheet("Master")

    sorted_entries = tuple(
        sorted(entries, key=_entry_sort_key)
    )

    _write_sheet(worksheet, sorted_entries)

    return _save(workbook, output_path)


def export_day_workbook(
    entries: tuple[TimetableViewEntry, ...],
    output_path: str | Path,
) -> Path:
    """Export one worksheet per day."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = _create_workbook()

    entries_by_day: dict[
        str,
        list[TimetableViewEntry],
    ] = defaultdict(list)

    for entry in entries:
        entries_by_day[entry.day.value].append(entry)

    for day_name in _DAY_ORDER:
        day_entries = entries_by_day.get(day_name, [])

        worksheet = workbook.create_sheet(
            _safe_sheet_name(
                day_name.title(),
                day_name.title(),
            )
        )

        sorted_entries = tuple(
            sorted(
                day_entries,
                key=lambda entry: (
                    entry.start_period,
                    entry.course_code,
                    entry.academic_group_code,
                    entry.session_id,
                ),
            )
        )

        _write_sheet(worksheet, sorted_entries)

    return _save(workbook, output_path)


def export_faculty_workbook(
    entries: tuple[TimetableViewEntry, ...],
    output_path: str | Path,
) -> Path:
    """Export one worksheet per faculty member."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = _create_workbook()

    entries_by_faculty: dict[
        str,
        list[TimetableViewEntry],
    ] = defaultdict(list)

    for entry in entries:
        entries_by_faculty[entry.faculty_name].append(entry)

    for faculty_name in sorted(entries_by_faculty):
        faculty_entries = entries_by_faculty[faculty_name]

        worksheet = workbook.create_sheet(
            _safe_sheet_name(
                faculty_name,
                "Faculty",
            )
        )

        sorted_entries = tuple(
            sorted(
                faculty_entries,
                key=_entry_sort_key,
            )
        )

        _write_sheet(worksheet, sorted_entries)

    return _save(workbook, output_path)


# ---------------------------------------------------------------------------
# Grid exports (days x periods), the format people print
# ---------------------------------------------------------------------------


def _unique_sheet_name(workbook: Workbook, name: str, fallback: str) -> str:
    base = _safe_sheet_name(name, fallback)
    candidate = base
    counter = 2

    while candidate in workbook.sheetnames:
        suffix = f" ({counter})"
        candidate = base[: 31 - len(suffix)] + suffix
        counter += 1

    return candidate


def _cell_text(entry: TimetableViewEntry, by: str) -> str:
    parts = [entry.subject_name]

    if by != "group":
        parts.append(entry.academic_group_code)
    if by != "faculty":
        parts.append(entry.faculty_name)
    if by != "room":
        parts.append(entry.room_name or "ONLINE")

    return "\n".join(parts)


def _related_codes(code: str, parents: dict[str, str | None]) -> set[str]:
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


def export_grid_workbook(
    entries: tuple[TimetableViewEntry, ...],
    output_path: str | Path,
    *,
    by: str,
    days: Iterable[str],
    periods_per_day: int,
    group_parents: dict[str, str | None] | None = None,
) -> Path:
    """Export one days x periods grid per group, faculty member or room.

    ``by`` is ``"group"``, ``"faculty"`` or ``"room"``. For groups,
    ``group_parents`` (code -> parent code) makes each sheet also show the
    sessions of ancestor and descendant groups, i.e. everything the
    students of that group attend.
    """

    if by not in {"group", "faculty", "room"}:
        raise ValueError(f"Unsupported grid export: {by!r}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    days = list(days)
    parents = group_parents or {}

    if by == "group":
        keys = sorted({entry.academic_group_code for entry in entries} | set(parents))
    elif by == "faculty":
        keys = sorted({entry.faculty_name for entry in entries})
    else:
        keys = sorted({entry.room_name for entry in entries if entry.room_name is not None})

    workbook = _create_workbook()

    header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")

    for key in keys:
        if by == "group":
            related = _related_codes(key, parents)
            selected = [entry for entry in entries if entry.academic_group_code in related]
        elif by == "faculty":
            selected = [entry for entry in entries if entry.faculty_name == key]
        else:
            selected = [entry for entry in entries if entry.room_name == key]

        if not selected:
            continue

        cells: dict[tuple[str, int], list[str]] = defaultdict(list)

        for entry in sorted(selected, key=_entry_sort_key):
            for period in range(entry.start_period, entry.end_period + 1):
                cells[(entry.day.value, period)].append(_cell_text(entry, by))

        worksheet = workbook.create_sheet(_unique_sheet_name(workbook, key, by.title()))
        worksheet.append(["Day", *(f"P{period}" for period in range(1, periods_per_day + 1))])

        for day in days:
            worksheet.append(
                [
                    day.title(),
                    *(
                        "\n---\n".join(cells.get((day, period), []))
                        for period in range(1, periods_per_day + 1)
                    ),
                ]
            )

        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for row in worksheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
            row[0].font = Font(bold=True)

        worksheet.column_dimensions["A"].width = 12
        for index in range(periods_per_day):
            worksheet.column_dimensions[get_column_letter(index + 2)].width = 24

        worksheet.page_setup.orientation = "landscape"
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 1
        worksheet.sheet_properties.pageSetUpPr.fitToPage = True

    return _save(workbook, output_path)
