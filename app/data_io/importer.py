"""Import a filled-in data workbook into the database.

The whole workbook is validated first. Every problem is collected with its
sheet, row and column, and nothing is written unless the workbook is
error-free. A successful import replaces all scheduling data in a single
transaction (timetable run history is kept).
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data_io.spec import SHEETS, SHEETS_BY_NAME, Column, Sheet
from app.db.models import (
    AcademicGroup,
    AssignmentMode,
    Course,
    Faculty,
    FacultyDesignation,
    GroupBlockedSlot,
    GroupType,
    ResourceType,
    Room,
    RoomType,
    School,
    SessionLock,
    Subject,
    SubjectType,
    TeachingAssignment,
    Unavailability,
    Weekday,
)
from app.db.models.faculty import FacultyTimePreference

logger = logging.getLogger("timetable.import")

_TRUE = {"true", "yes", "y", "1", "t"}
_FALSE = {"false", "no", "n", "0", "f"}


@dataclass(frozen=True)
class ImportIssue:
    sheet: str
    row: int | None
    column: str | None
    message: str

    def __str__(self) -> str:
        where = self.sheet
        if self.row is not None:
            where += f" row {self.row}"
        if self.column:
            where += f", {self.column}"
        return f"{where}: {self.message}"


@dataclass
class ImportResult:
    ok: bool
    counts: dict[str, int] = field(default_factory=dict)
    issues: list[ImportIssue] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "counts": self.counts,
            "issues": [issue.__dict__ for issue in self.issues],
        }


Record = dict[str, object]


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _normalise_header(value: object) -> str:
    return str(value or "").strip().rstrip("*").strip().lower().replace(" ", "_")


def _cell_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    return text or None


def _convert(column: Column, raw: object) -> tuple[object, str | None]:
    """Return ``(value, error)`` for one cell."""

    text = _cell_text(raw)

    if text is None:
        if column.required:
            return None, "is required"
        return column.default, None

    if column.kind in ("text", "ref"):
        if column.max_length and len(text) > column.max_length:
            return None, f"is longer than {column.max_length} characters"
        return text, None

    if column.kind == "int":
        try:
            number = float(text)
        except ValueError:
            return None, f"must be a whole number, got {text!r}"
        if not number.is_integer():
            return None, f"must be a whole number, got {text!r}"
        number = int(number)
        if column.min_value is not None and number < column.min_value:
            return None, f"must be at least {column.min_value}, got {number}"
        return number, None

    if column.kind == "bool":
        lowered = text.lower()
        if lowered in _TRUE:
            return True, None
        if lowered in _FALSE:
            return False, None
        return None, f"must be TRUE or FALSE, got {text!r}"

    if column.kind == "enum":
        candidate = text.upper().replace(" ", "_").replace("-", "_")
        if candidate in column.choices:
            return candidate, None
        return None, f"must be one of {', '.join(column.choices)}; got {text!r}"

    raise AssertionError(column.kind)


def parse_workbook(data: bytes) -> tuple[dict[str, list[tuple[int, Record]]], list[ImportIssue]]:
    """Read every data sheet into ``(row_number, record)`` pairs."""

    issues: list[ImportIssue] = []

    try:
        workbook = load_workbook(BytesIO(data), read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, KeyError, OSError) as exc:
        return {}, [ImportIssue("(file)", None, None, f"Not a valid .xlsx workbook: {exc}")]

    parsed: dict[str, list[tuple[int, Record]]] = {}
    sheet_lookup = {name.strip().lower(): name for name in workbook.sheetnames}

    for spec in SHEETS:
        actual = sheet_lookup.get(spec.name.lower())
        if actual is None:
            if not spec.optional:
                issues.append(ImportIssue(spec.name, None, None, "sheet is missing"))
            parsed[spec.name] = []
            continue

        rows = workbook[actual].iter_rows(values_only=True)
        header = next(rows, None)
        if header is None:
            parsed[spec.name] = []
            continue

        positions: dict[str, int] = {}
        for index, value in enumerate(header):
            name = _normalise_header(value)
            if name:
                positions.setdefault(name, index)

        missing = [column.name for column in spec.columns if column.name not in positions]
        required_missing = [name for name in missing if spec.column(name).required]
        if required_missing:
            issues.append(
                ImportIssue(
                    spec.name,
                    1,
                    None,
                    f"missing required column(s): {', '.join(required_missing)}",
                )
            )
            parsed[spec.name] = []
            continue

        records: list[tuple[int, Record]] = []
        for row_number, values in enumerate(rows, start=2):
            if values is None or all(_cell_text(value) is None for value in values):
                continue
            record: Record = {}
            for column in spec.columns:
                index = positions.get(column.name)
                raw = values[index] if index is not None and index < len(values) else None
                value, error = _convert(column, raw)
                if error:
                    issues.append(ImportIssue(spec.name, row_number, column.name, error))
                record[column.name] = value
            records.append((row_number, record))
        parsed[spec.name] = records

    workbook.close()
    return parsed, issues


# ---------------------------------------------------------------------------
# Cross-row validation
# ---------------------------------------------------------------------------


def _check_unique(spec: Sheet, rows, column: str, issues: list[ImportIssue]) -> set[str]:
    seen: dict[str, int] = {}
    for row_number, record in rows:
        value = record.get(column)
        if value is None:
            continue
        key = str(value).lower()
        if key in seen:
            issues.append(
                ImportIssue(
                    spec.name,
                    row_number,
                    column,
                    f"duplicate {column} {value!r} (first used on row {seen[key]})",
                )
            )
        else:
            seen[key] = row_number
    return {str(record[column]) for _, record in rows if record.get(column) is not None}


def validate(parsed: dict[str, list[tuple[int, Record]]]) -> list[ImportIssue]:
    issues: list[ImportIssue] = []
    sheet = SHEETS_BY_NAME

    codes = {
        "Schools": _check_unique(sheet["Schools"], parsed["Schools"], "code", issues),
        "Courses": _check_unique(sheet["Courses"], parsed["Courses"], "code", issues),
        "Faculty": _check_unique(sheet["Faculty"], parsed["Faculty"], "employee_id", issues),
        "Rooms": _check_unique(sheet["Rooms"], parsed["Rooms"], "code", issues),
        "Subjects": _check_unique(sheet["Subjects"], parsed["Subjects"], "code", issues),
        "Groups": _check_unique(sheet["Groups"], parsed["Groups"], "code", issues),
    }
    _check_unique(sheet["Faculty"], parsed["Faculty"], "email", issues)

    for spec in SHEETS:
        for row_number, record in parsed[spec.name]:
            for column in spec.columns:
                value = record.get(column.name)
                if column.kind != "ref" or value is None:
                    continue
                if str(value) not in codes[column.ref_sheet]:
                    issues.append(
                        ImportIssue(
                            spec.name,
                            row_number,
                            column.name,
                            f"{value!r} is not a code on the {column.ref_sheet} sheet",
                        )
                    )

    # Groups: parent must be in the same course; no cycles.
    groups = {
        record["code"]: (row, record) for row, record in parsed["Groups"] if record.get("code")
    }
    for code, (row_number, record) in groups.items():
        parent = record.get("parent_group_code")
        if parent is None:
            continue
        if parent == code:
            issues.append(
                ImportIssue(
                    "Groups", row_number, "parent_group_code", "a group cannot be its own parent"
                )
            )
            continue
        if parent in groups and groups[parent][1].get("course_code") != record.get("course_code"):
            issues.append(
                ImportIssue(
                    "Groups",
                    row_number,
                    "parent_group_code",
                    "parent group must belong to the same course",
                )
            )
        seen = {code}
        current = parent
        while current in groups:
            if current in seen:
                issues.append(
                    ImportIssue(
                        "Groups",
                        row_number,
                        "parent_group_code",
                        "group hierarchy contains a cycle",
                    )
                )
                break
            seen.add(current)
            current = groups[current][1].get("parent_group_code")

    # Assignments: in-person sessions need a room type.
    for row_number, record in parsed["Assignments"]:
        if record.get("mode") in ("IN_PERSON", "EITHER") and not record.get("required_room_type"):
            issues.append(
                ImportIssue(
                    "Assignments",
                    row_number,
                    "required_room_type",
                    f"required when mode is {record.get('mode')}",
                )
            )

    # Unavailability references depend on resource_type.
    for row_number, record in parsed["Unavailability"]:
        kind = record.get("resource_type")
        code = record.get("resource_code")
        if code is None or kind is None:
            continue
        pool = codes["Faculty"] if kind == "FACULTY" else codes["Rooms"]
        if str(code) not in pool:
            label = "Faculty employee_id" if kind == "FACULTY" else "Rooms code"
            issues.append(
                ImportIssue(
                    "Unavailability", row_number, "resource_code", f"{code!r} is not a {label}"
                )
            )
        start, end = record.get("start_period"), record.get("end_period")
        if isinstance(start, int) and isinstance(end, int) and end < start:
            issues.append(
                ImportIssue(
                    "Unavailability", row_number, "end_period", "must not be before start_period"
                )
            )

    # Session locks must identify exactly one assignment.
    assignment_keys = Counter(
        (record.get("subject_code"), record.get("group_code"))
        for _, record in parsed["Assignments"]
    )
    full_keys = {
        (
            record.get("subject_code"),
            record.get("group_code"),
            record.get("faculty_employee_id"),
        ): record
        for _, record in parsed["Assignments"]
    }
    lock_seen: set[tuple] = set()
    for row_number, record in parsed["SessionLocks"]:
        key = (record.get("subject_code"), record.get("group_code"))
        faculty = record.get("faculty_employee_id")
        if faculty is None:
            matches = assignment_keys.get(key, 0)
            if matches == 0:
                issues.append(
                    ImportIssue(
                        "SessionLocks", row_number, None, "no assignment for this subject and group"
                    )
                )
                continue
            if matches > 1:
                issues.append(
                    ImportIssue(
                        "SessionLocks",
                        row_number,
                        "faculty_employee_id",
                        "several assignments match this subject and group; "
                        "give the faculty_employee_id",
                    )
                )
                continue
            assignment = next(value for k, value in full_keys.items() if k[:2] == key)
        else:
            assignment = full_keys.get((*key, faculty))
            if assignment is None:
                issues.append(
                    ImportIssue(
                        "SessionLocks",
                        row_number,
                        None,
                        "no assignment for this subject, group and faculty",
                    )
                )
                continue
        number = record.get("session_number")
        sessions = assignment.get("sessions_per_week")
        if isinstance(number, int) and isinstance(sessions, int) and number > sessions:
            issues.append(
                ImportIssue(
                    "SessionLocks",
                    row_number,
                    "session_number",
                    f"assignment has only {sessions} sessions per week",
                )
            )
        lock_key = (*key, assignment.get("faculty_employee_id"), number)
        if lock_key in lock_seen:
            issues.append(
                ImportIssue(
                    "SessionLocks", row_number, "session_number", "this session is locked twice"
                )
            )
        lock_seen.add(lock_key)

    return issues


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def _replace_all(db: Session, parsed: dict[str, list[tuple[int, Record]]]) -> dict[str, int]:
    now = datetime.now(UTC)
    stamp = {"created_at": now, "updated_at": now}

    for model in (
        SessionLock,
        GroupBlockedSlot,
        Unavailability,
        TeachingAssignment,
        AcademicGroup,
        Subject,
        Room,
        Faculty,
        Course,
        School,
    ):
        if model is AcademicGroup:
            db.query(AcademicGroup).update({AcademicGroup.parent_group_id: None})
        db.execute(delete(model))
    db.flush()

    def records(name: str) -> list[Record]:
        return [record for _, record in parsed[name]]

    schools = {}
    for record in records("Schools"):
        schools[record["code"]] = School(
            code=record["code"], name=record["name"], is_active=record["is_active"], **stamp
        )
    db.add_all(schools.values())
    db.flush()

    courses = {}
    for record in records("Courses"):
        courses[record["code"]] = Course(
            code=record["code"],
            name=record["name"],
            school_id=schools[record["school_code"]].id,
            duration_years=record["duration_years"],
            total_semesters=record["total_semesters"],
            is_active=record["is_active"],
            **stamp,
        )
    faculty = {}
    for record in records("Faculty"):
        faculty[record["employee_id"]] = Faculty(
            employee_id=record["employee_id"],
            name=record["name"],
            email=record["email"],
            designation=FacultyDesignation(record["designation"]),
            time_preference=FacultyTimePreference(record["time_preference"] or "ANY"),
            preferred_day_off=Weekday(record["preferred_day_off"])
            if record["preferred_day_off"]
            else None,
            school_id=schools[record["school_code"]].id,
            is_active=record["is_active"],
            **stamp,
        )
    rooms = {}
    for record in records("Rooms"):
        rooms[record["code"]] = Room(
            code=record["code"],
            name=record["name"],
            room_type=RoomType(record["room_type"]),
            capacity=record["capacity"],
            school_id=schools[record["school_code"]].id,
            is_shared=bool(record["is_shared"]),
            is_active=record["is_active"],
            **stamp,
        )
    subjects = {}
    for record in records("Subjects"):
        subjects[record["code"]] = Subject(
            code=record["code"],
            name=record["name"],
            subject_type=SubjectType(record["subject_type"]),
            is_active=record["is_active"],
            **stamp,
        )
    db.add_all([*courses.values(), *faculty.values(), *rooms.values(), *subjects.values()])
    db.flush()

    groups = {}
    for record in records("Groups"):
        groups[record["code"]] = AcademicGroup(
            code=record["code"],
            name=record["name"],
            group_type=GroupType(record["group_type"]),
            course_id=courses[record["course_code"]].id,
            capacity=record["capacity"],
            is_active=record["is_active"],
            **stamp,
        )
    db.add_all(groups.values())
    db.flush()
    for record in records("Groups"):
        if record["parent_group_code"]:
            groups[record["code"]].parent_group_id = groups[record["parent_group_code"]].id

    assignments: dict[tuple, TeachingAssignment] = {}
    by_subject_group: dict[tuple, list[TeachingAssignment]] = defaultdict(list)
    for record in records("Assignments"):
        group = groups[record["group_code"]]
        assignment = TeachingAssignment(
            subject_id=subjects[record["subject_code"]].id,
            course_id=group.course_id,
            academic_group_id=group.id,
            faculty_id=faculty[record["faculty_employee_id"]].id,
            sessions_per_week=record["sessions_per_week"],
            duration_periods=record["duration_periods"],
            mode=AssignmentMode(record["mode"]),
            required_room_type=record["required_room_type"],
            allow_across_lunch=record["allow_across_lunch"],
            is_active=record["is_active"],
            **stamp,
        )
        assignments[
            (record["subject_code"], record["group_code"], record["faculty_employee_id"])
        ] = assignment
        by_subject_group[(record["subject_code"], record["group_code"])].append(assignment)
    db.add_all(assignments.values())
    db.flush()

    for record in records("Unavailability"):
        kind = ResourceType(record["resource_type"])
        resource = (
            faculty[record["resource_code"]]
            if kind == ResourceType.FACULTY
            else rooms[record["resource_code"]]
        )
        db.add(
            Unavailability(
                resource_type=kind,
                resource_id=resource.id,
                day=Weekday(record["day"]),
                start_period=record["start_period"],
                end_period=record["end_period"],
                reason=record["reason"],
                **stamp,
            )
        )

    for record in records("GroupBlockedSlots"):
        db.add(
            GroupBlockedSlot(
                academic_group_id=groups[record["group_code"]].id,
                day=Weekday(record["day"]),
                period=record["period"],
                label=record["label"],
                **stamp,
            )
        )

    for record in records("SessionLocks"):
        if record["faculty_employee_id"]:
            assignment = assignments[
                (record["subject_code"], record["group_code"], record["faculty_employee_id"])
            ]
        else:
            assignment = by_subject_group[(record["subject_code"], record["group_code"])][0]
        db.add(
            SessionLock(
                teaching_assignment_id=assignment.id,
                session_number=record["session_number"],
                day=Weekday(record["day"]),
                start_period=record["start_period"],
                room_id=rooms[record["room_code"]].id if record["room_code"] else None,
                **stamp,
            )
        )

    db.flush()
    return {spec.name: len(parsed[spec.name]) for spec in SHEETS}


def import_workbook(db: Session, data: bytes) -> ImportResult:
    """Validate and, if valid, replace all scheduling data with the workbook's."""

    parsed, issues = parse_workbook(data)

    if not issues:
        issues = validate(parsed)

    if issues:
        logger.warning("Workbook import rejected with %d issue(s)", len(issues))
        return ImportResult(ok=False, issues=issues)

    try:
        counts = _replace_all(db, parsed)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Workbook import failed with a database constraint error")
        return ImportResult(
            ok=False,
            issues=[ImportIssue("(database)", None, None, f"constraint violated: {exc.orig}")],
        )
    except Exception:
        db.rollback()
        logger.exception("Workbook import failed")
        raise

    logger.info("Imported workbook: %s", counts)
    return ImportResult(ok=True, counts=counts)
