"""Write data workbooks: the blank template and exports of the current data."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from io import BytesIO

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_io.spec import INSTRUCTIONS_SHEET, SHEETS, Column, Sheet
from app.db.models import (
    AcademicGroup,
    Course,
    Faculty,
    GroupBlockedSlot,
    ResourceType,
    Room,
    School,
    SessionLock,
    Subject,
    TeachingAssignment,
    Unavailability,
)

REQUIRED_FILL = PatternFill(fill_type="solid", fgColor="1F4E78")
OPTIONAL_FILL = PatternFill(fill_type="solid", fgColor="5B7FA6")
HEADER_FONT = Font(bold=True, color="FFFFFF")
VALIDATION_ROWS = 2000

Rows = Mapping[str, Sequence[Mapping[str, object]]]


def _kind_label(column: Column) -> str:
    if column.kind == "ref":
        return f"code from {column.ref_sheet}"
    if column.kind == "bool":
        return "TRUE / FALSE"
    if column.kind == "enum":
        return "one of the listed values"
    if column.kind == "int":
        return "whole number" + (f" ≥ {column.min_value}" if column.min_value else "")
    return "text"


def _write_instructions(workbook: Workbook) -> None:
    sheet = workbook.create_sheet(INSTRUCTIONS_SHEET)
    lines = [
        ("Open Timetable Generator: data workbook", True),
        ("", False),
        ("1. Fill in one row per record on each sheet. Do not rename sheets or headers.", False),
        ("2. Dark blue headers are required columns; lighter headers are optional.", False),
        (
            "3. Records refer to each other by code (school code, group code, employee ID, ...).",
            False,
        ),
        ("4. Upload the file on the Import page. Importing REPLACES all existing data.", False),
        (
            "5. Nothing is changed if any row has an error; every error is listed with its sheet,",
            False,
        ),
        ("   row and column.", False),
        ("6. Unavailability, GroupBlockedSlots and SessionLocks may be left empty.", False),
        ("", False),
    ]
    for text, bold in lines:
        sheet.append([text])
        if bold:
            sheet.cell(sheet.max_row, 1).font = Font(bold=True, size=14)

    for spec in SHEETS:
        sheet.append([])
        sheet.append([spec.name, spec.description])
        sheet.cell(sheet.max_row, 1).font = Font(bold=True, size=12)
        sheet.append(["Column", "Required", "Type", "Allowed values", "Notes"])
        for cell in sheet[sheet.max_row]:
            cell.font = Font(bold=True)
        for column in spec.columns:
            sheet.append(
                [
                    column.name,
                    "yes" if column.required else "",
                    _kind_label(column),
                    ", ".join(column.choices) if column.choices else "",
                    column.description,
                ]
            )

    for letter, width in {"A": 26, "B": 18, "C": 24, "D": 60, "E": 70}.items():
        sheet.column_dimensions[letter].width = width


def _write_sheet(workbook: Workbook, spec: Sheet, rows: Sequence[Mapping[str, object]]) -> None:
    sheet = workbook.create_sheet(spec.name)
    sheet.append([column.name for column in spec.columns])

    for index, column in enumerate(spec.columns, start=1):
        cell = sheet.cell(1, index)
        cell.fill = REQUIRED_FILL if column.required else OPTIONAL_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
        note = column.description or _kind_label(column)
        if column.required:
            note = f"Required. {note}"
        cell.comment = Comment(note, "Timetable Generator")
        letter = get_column_letter(index)
        sheet.column_dimensions[letter].width = max(14, len(column.name) + 4)

        choices = (
            column.choices
            if column.kind == "enum"
            else ("TRUE", "FALSE")
            if column.kind == "bool"
            else ()
        )
        if choices:
            validation = DataValidation(
                type="list",
                formula1='"' + ",".join(choices) + '"',
                allow_blank=not column.required,
                showErrorMessage=True,
                errorTitle="Invalid value",
                error=f"{column.name} must be one of: {', '.join(choices)}",
            )
            validation.add(f"{letter}2:{letter}{VALIDATION_ROWS}")
            sheet.add_data_validation(validation)
        elif column.kind == "int":
            validation = DataValidation(
                type="whole",
                operator="greaterThanOrEqual",
                formula1=str(column.min_value or 0),
                allow_blank=not column.required,
                showErrorMessage=True,
                error=f"{column.name} must be a whole number",
            )
            validation.add(f"{letter}2:{letter}{VALIDATION_ROWS}")
            sheet.add_data_validation(validation)

    for row in rows:
        values = []
        for column in spec.columns:
            value = row.get(column.name)
            if column.kind == "bool" and value is not None:
                value = "TRUE" if value else "FALSE"
            values.append(value)
        sheet.append(values)

    sheet.freeze_panes = "A2"


def build_workbook(rows: Rows | None = None) -> Workbook:
    """Build a data workbook; without ``rows`` it is the blank template."""

    workbook = Workbook()
    workbook.remove(workbook.active)
    _write_instructions(workbook)
    for spec in SHEETS:
        _write_sheet(workbook, spec, (rows or {}).get(spec.name, ()))
    workbook.active = 0
    return workbook


def workbook_bytes(workbook: Workbook) -> bytes:
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def export_rows(db: Session) -> dict[str, list[dict[str, object]]]:
    """Current database contents in workbook form (codes instead of IDs)."""

    def all_of(model):
        return list(db.scalars(select(model).order_by(model.id)).all())

    schools = all_of(School)
    courses = all_of(Course)
    faculty = all_of(Faculty)
    rooms = all_of(Room)
    subjects = all_of(Subject)
    groups = all_of(AcademicGroup)
    assignments = all_of(TeachingAssignment)

    school_code = {item.id: item.code for item in schools}
    course_code = {item.id: item.code for item in courses}
    faculty_code = {item.id: item.employee_id for item in faculty}
    room_code = {item.id: item.code for item in rooms}
    subject_code = {item.id: item.code for item in subjects}
    group_code = {item.id: item.code for item in groups}
    assignment_by_id = {item.id: item for item in assignments}

    def value(enum_value):
        return enum_value.value if enum_value is not None else None

    rows: dict[str, list[dict[str, object]]] = {
        "Schools": [
            {"code": item.code, "name": item.name, "is_active": item.is_active} for item in schools
        ],
        "Courses": [
            {
                "code": item.code,
                "name": item.name,
                "school_code": school_code.get(item.school_id),
                "duration_years": item.duration_years,
                "total_semesters": item.total_semesters,
                "is_active": item.is_active,
            }
            for item in courses
        ],
        "Faculty": [
            {
                "employee_id": item.employee_id,
                "name": item.name,
                "email": item.email,
                "designation": value(item.designation),
                "time_preference": value(item.time_preference),
                "preferred_day_off": value(item.preferred_day_off),
                "school_code": school_code.get(item.school_id),
                "is_active": item.is_active,
            }
            for item in faculty
        ],
        "Rooms": [
            {
                "code": item.code,
                "name": item.name,
                "room_type": value(item.room_type),
                "capacity": item.capacity,
                "school_code": school_code.get(item.school_id),
                "is_shared": item.is_shared,
                "is_active": item.is_active,
            }
            for item in rooms
        ],
        "Subjects": [
            {
                "code": item.code,
                "name": item.name,
                "subject_type": value(item.subject_type),
                "is_active": item.is_active,
            }
            for item in subjects
        ],
        "Groups": [
            {
                "code": item.code,
                "name": item.name,
                "group_type": value(item.group_type),
                "course_code": course_code.get(item.course_id),
                "parent_group_code": group_code.get(item.parent_group_id),
                "capacity": item.capacity,
                "is_active": item.is_active,
            }
            for item in groups
        ],
        "Assignments": [
            {
                "subject_code": subject_code.get(item.subject_id),
                "group_code": group_code.get(item.academic_group_id),
                "faculty_employee_id": faculty_code.get(item.faculty_id),
                "sessions_per_week": item.sessions_per_week,
                "duration_periods": item.duration_periods,
                "mode": value(item.mode),
                "required_room_type": item.required_room_type,
                "allow_across_lunch": item.allow_across_lunch,
                "is_active": item.is_active,
            }
            for item in assignments
        ],
        "Unavailability": [
            {
                "resource_type": value(item.resource_type),
                "resource_code": (
                    faculty_code.get(item.resource_id)
                    if item.resource_type == ResourceType.FACULTY
                    else room_code.get(item.resource_id)
                ),
                "day": value(item.day),
                "start_period": item.start_period,
                "end_period": item.end_period,
                "reason": item.reason,
            }
            for item in all_of(Unavailability)
        ],
        "GroupBlockedSlots": [
            {
                "group_code": group_code.get(item.academic_group_id),
                "day": value(item.day),
                "period": item.period,
                "label": item.label,
            }
            for item in all_of(GroupBlockedSlot)
        ],
        "SessionLocks": [],
    }

    for item in all_of(SessionLock):
        assignment = assignment_by_id.get(item.teaching_assignment_id)
        if assignment is None:
            continue
        rows["SessionLocks"].append(
            {
                "subject_code": subject_code.get(assignment.subject_id),
                "group_code": group_code.get(assignment.academic_group_id),
                "faculty_employee_id": faculty_code.get(assignment.faculty_id),
                "session_number": item.session_number,
                "day": value(item.day),
                "start_period": item.start_period,
                "room_code": room_code.get(item.room_id),
            }
        )

    return rows
