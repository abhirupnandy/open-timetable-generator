"""Printable PDF timetables: one landscape A4 page per group, faculty or room.

The layout matches the grid workbooks and the web view: days down the
side, periods (with clock times) across, multi-period sessions merged,
a lunch column, a colour per subject and the daily / weekly load.
"""

from __future__ import annotations

import zlib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.domain.timetable_views import TimetableViewEntry
from app.export.layout import (
    Entity,
    ExportCalendar,
    cell_lines,
    day_cells,
    day_title,
    entities,
    entries_for,
)

NAVY = colors.HexColor("#1F4E78")
GRID = colors.HexColor("#BFBFBF")
DAY_BG = colors.HexColor("#DDE7F0")
LUNCH_BG = colors.HexColor("#EDEDED")
BLOCKED_BG = colors.HexColor("#F2F2F2")
LOAD_BG = colors.HexColor("#FFF2CC")
SUBJECT_COLOURS = tuple(
    colors.HexColor(f"#{value}")
    for value in (
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
)

TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=NAVY)
SUBTITLE = ParagraphStyle(
    "subtitle", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#595959")
)
HEAD = ParagraphStyle(
    "head",
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10,
    alignment=TA_CENTER,
    textColor=colors.white,
)
DAY = ParagraphStyle("day", fontName="Helvetica-Bold", fontSize=9, leading=11, alignment=TA_CENTER)
CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=7, leading=8.6)
CELL_SMALL = ParagraphStyle("cell_small", parent=CELL, fontSize=6, leading=7.2)
BLOCKED = ParagraphStyle(
    "blocked",
    parent=CELL,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#595959"),
    fontName="Helvetica-Oblique",
)
LOAD = ParagraphStyle(
    "load", fontName="Helvetica-Bold", fontSize=9, leading=11, alignment=TA_CENTER
)


def _subject_colour(subject: str):
    return SUBJECT_COLOURS[zlib.crc32(subject.encode()) % len(SUBJECT_COLOURS)]


def _cell_paragraph(entries: Sequence[TimetableViewEntry], by: str) -> Paragraph:
    blocks = []
    for entry in entries:
        title, details = cell_lines(entry, by)
        lines = [f"<b>{escape(title)}</b>"]
        lines += [f'<font color="#404040">{escape(detail)}</font>' for detail in details]
        blocks.append("<br/>".join(lines))
    style = CELL_SMALL if len(entries) > 2 else CELL
    return Paragraph("<br/><br/>".join(blocks), style)


def _grid_table(
    entries: Sequence[TimetableViewEntry],
    calendar: ExportCalendar,
    by: str,
    width: float,
) -> Table:
    periods = list(calendar.periods)
    lunch = calendar.lunch_after_period

    column_of: dict[int, int] = {}
    column = 1
    lunch_column = None
    for period in periods:
        column_of[period] = column
        column += 1
        if period == lunch:
            lunch_column = column
            column += 1
    load_column = column
    columns = load_column + 1

    header: list = [Paragraph("Day", HEAD)] + [""] * (columns - 1)
    for period in periods:
        header[column_of[period]] = Paragraph(
            escape(calendar.period_header(period)).replace("\n", "<br/>"), HEAD
        )
    if lunch_column is not None:
        header[lunch_column] = Paragraph("L<br/>u<br/>n<br/>c<br/>h", HEAD)
    header[load_column] = Paragraph("Load", HEAD)

    rows = [header]
    styles: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ("VALIGN", (0, 1), (0, -1), "MIDDLE"),
        ("VALIGN", (load_column, 1), (load_column, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (0, len(calendar.days)), DAY_BG),
        ("BACKGROUND", (load_column, 1), (load_column, -1), LOAD_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if lunch_column is not None:
        styles.append(
            ("BACKGROUND", (lunch_column, 1), (lunch_column, len(calendar.days)), LUNCH_BG)
        )

    by_day: dict[str, list[TimetableViewEntry]] = defaultdict(list)
    for entry in entries:
        by_day[entry.day.value].append(entry)

    weekly = 0
    for row_index, day in enumerate(calendar.days, start=1):
        row: list = [Paragraph(day_title(day), DAY)] + [""] * (columns - 1)
        busy: set[int] = set()
        for cell in day_cells(by_day.get(day, []), day, calendar):
            start = column_of[cell.period]
            end = column_of[cell.period + cell.span - 1]
            if cell.blocked_label is not None:
                row[start] = Paragraph(escape(cell.blocked_label), BLOCKED)
                styles.append(("BACKGROUND", (start, row_index), (start, row_index), BLOCKED_BG))
            elif cell.entries:
                row[start] = _cell_paragraph(cell.entries, by)
                colour = _subject_colour(cell.entries[0].subject_name)
                styles.append(("BACKGROUND", (start, row_index), (end, row_index), colour))
                busy.update(range(cell.period, cell.period + cell.span))
            if end > start:
                styles.append(("SPAN", (start, row_index), (end, row_index)))
        row[load_column] = Paragraph(str(len(busy)), LOAD)
        weekly += len(busy)
        rows.append(row)

    footer: list = [""] * columns
    footer[load_column - 1] = Paragraph("Weekly", LOAD)
    footer[load_column] = Paragraph(str(weekly), LOAD)
    rows.append(footer)
    last = len(rows) - 1
    styles += [
        ("GRID", (0, last), (-1, last), 0, colors.white),
        ("BOX", (load_column, last), (load_column, last), 0.5, GRID),
        ("SPAN", (0, last), (load_column - 2, last)),
    ]

    day_width = 20 * mm
    lunch_width = 7 * mm if lunch_column is not None else 0
    load_width = 13 * mm
    period_width = (width - day_width - lunch_width - load_width) / max(len(periods), 1)
    widths = [day_width] + [period_width] * (columns - 1)
    if lunch_column is not None:
        widths[lunch_column] = lunch_width
    widths[load_column] = load_width

    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle(styles))
    return table


def timetable_pdf(
    entries: Sequence[TimetableViewEntry],
    calendar: ExportCalendar,
    *,
    by: str,
    keys: Sequence[str] | None = None,
    group_parents: Mapping[str, str | None] | None = None,
    heading: str = "Timetable",
    footer: str = "",
) -> bytes:
    """Render one page per entity of view ``by`` (all of them, or ``keys``)."""

    selected: list[Entity] = entities(entries, by, group_parents)
    if keys is not None:
        wanted = set(keys)
        selected = [entity for entity in selected if entity.key in wanted]

    buffer = BytesIO()
    page_width, page_height = landscape(A4)
    margin = 10 * mm
    footer_text = footer or f"Printed {datetime.now():%d %b %Y %H:%M}"

    def draw_footer(canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#808080"))
        canvas.drawString(margin, 6 * mm, footer_text)
        canvas.drawRightString(page_width - margin, 6 * mm, f"Page {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        buffer,
        pagesize=(page_width, page_height),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=12 * mm,
        title=heading,
        author="Open Timetable Generator",
    )
    width = page_width - 2 * margin

    story: list = []
    for index, entity in enumerate(selected):
        shown = entries_for(entries, by, entity.key, group_parents)
        if index:
            story.append(PageBreak())
        story.append(Paragraph(f"{escape(heading)}: {escape(entity.title)}", TITLE))
        details = [entity.subtitle] if entity.subtitle else []
        details.append(f"{by.title()} view · {len(shown)} sessions")
        if by == "group":
            details.append("includes parent-group and batch sessions")
        story.append(Paragraph(escape(" · ".join(details)), SUBTITLE))
        story.append(Spacer(1, 4 * mm))
        story.append(_grid_table(shown, calendar, by, width))

    if not story:
        story.append(Paragraph("Nothing to print.", TITLE))

    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return buffer.getvalue()
