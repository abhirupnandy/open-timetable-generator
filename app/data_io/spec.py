"""Column specification of the data workbook (template, export and import).

Every sheet references other records by their human-readable code (school
code, course code, group code, faculty employee ID, room code), never by
database ID, so a workbook can be filled in by hand and imported into an
empty database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.db.models.academic_group import GroupType
from app.db.models.faculty import FacultyDesignation, FacultyTimePreference
from app.db.models.room import RoomType
from app.db.models.scheduling_rules import ResourceType, Weekday
from app.db.models.subject import SubjectType
from app.db.models.teaching_assignment import AssignmentMode

Kind = Literal["text", "int", "bool", "enum", "ref"]


@dataclass(frozen=True)
class Column:
    name: str
    kind: Kind = "text"
    required: bool = False
    description: str = ""
    choices: tuple[str, ...] = ()
    ref_sheet: str | None = None
    default: object = None
    min_value: int | None = None
    max_length: int | None = None


@dataclass(frozen=True)
class Sheet:
    name: str
    description: str
    columns: tuple[Column, ...]
    optional: bool = False
    keys: tuple[str, ...] = field(default=())

    def column(self, name: str) -> Column:
        return next(column for column in self.columns if column.name == name)


def _enum(enum) -> tuple[str, ...]:
    return tuple(item.value for item in enum)


ACTIVE = Column("is_active", "bool", default=True, description="TRUE / FALSE (default TRUE)")
DAY = Column("day", "enum", required=True, choices=_enum(Weekday))

SHEETS: tuple[Sheet, ...] = (
    Sheet(
        "Schools",
        "Institutional schools. Every course, faculty member and room belongs to one.",
        (
            Column("code", required=True, max_length=20, description="Unique short code"),
            Column("name", required=True, max_length=150),
            ACTIVE,
        ),
        keys=("code",),
    ),
    Sheet(
        "Courses",
        "Programmes offered by a school.",
        (
            Column("code", required=True, max_length=30, description="Unique course code"),
            Column("name", required=True, max_length=150),
            Column("school_code", "ref", required=True, ref_sheet="Schools"),
            Column("duration_years", "int", required=True, min_value=1),
            Column("total_semesters", "int", required=True, min_value=1),
            ACTIVE,
        ),
        keys=("code",),
    ),
    Sheet(
        "Faculty",
        "Teaching staff.",
        (
            Column("employee_id", required=True, max_length=50, description="Unique employee ID"),
            Column("name", required=True, max_length=150),
            Column("email", required=True, max_length=255, description="Unique email address"),
            Column("designation", "enum", required=True, choices=_enum(FacultyDesignation)),
            Column(
                "time_preference",
                "enum",
                choices=_enum(FacultyTimePreference),
                default="ANY",
                description="Preferred teaching time (default ANY)",
            ),
            Column(
                "preferred_day_off",
                "enum",
                choices=_enum(Weekday),
                description="Optional; used by the faculty_preferred_day_off soft constraint",
            ),
            Column("school_code", "ref", required=True, ref_sheet="Schools"),
            ACTIVE,
        ),
        keys=("employee_id",),
    ),
    Sheet(
        "Rooms",
        "Physical rooms.",
        (
            Column("code", required=True, max_length=30, description="Unique room code"),
            Column("name", required=True, max_length=150),
            Column("room_type", "enum", required=True, choices=_enum(RoomType)),
            Column("capacity", "int", required=True, min_value=1),
            Column("school_code", "ref", required=True, ref_sheet="Schools"),
            Column(
                "is_shared",
                "bool",
                default=False,
                description="Shared with other schools; record outside bookings as Unavailability",
            ),
            ACTIVE,
        ),
        keys=("code",),
    ),
    Sheet(
        "Subjects",
        "Subjects that can be taught.",
        (
            Column("code", required=True, max_length=30, description="Unique subject code"),
            Column("name", required=True, max_length=150),
            Column("subject_type", "enum", required=True, choices=_enum(SubjectType)),
            ACTIVE,
        ),
        keys=("code",),
    ),
    Sheet(
        "Groups",
        "Student groups and their batches. A batch names its parent group; a parent's "
        "sessions are attended by all of its batches.",
        (
            Column("code", required=True, max_length=50, description="Unique group code"),
            Column("name", required=True, max_length=150),
            Column("group_type", "enum", required=True, choices=_enum(GroupType)),
            Column("course_code", "ref", required=True, ref_sheet="Courses"),
            Column(
                "parent_group_code",
                "ref",
                ref_sheet="Groups",
                description="Optional parent group (same course)",
            ),
            Column("capacity", "int", min_value=1, description="Number of students"),
            ACTIVE,
        ),
        keys=("code",),
    ),
    Sheet(
        "Assignments",
        "What is taught to whom, by whom, and how often. The course is taken from the group.",
        (
            Column("subject_code", "ref", required=True, ref_sheet="Subjects"),
            Column("group_code", "ref", required=True, ref_sheet="Groups"),
            Column("faculty_employee_id", "ref", required=True, ref_sheet="Faculty"),
            Column("sessions_per_week", "int", required=True, min_value=1),
            Column("duration_periods", "int", required=True, min_value=1),
            Column("mode", "enum", required=True, choices=_enum(AssignmentMode)),
            Column(
                "required_room_type",
                "enum",
                choices=_enum(RoomType),
                description="Required for IN_PERSON and EITHER",
            ),
            Column(
                "allow_across_lunch",
                "bool",
                description="TRUE exempts this assignment from the lunch rule",
            ),
            ACTIVE,
        ),
    ),
    Sheet(
        "Unavailability",
        "Periods in which a faculty member or room cannot be used.",
        (
            Column("resource_type", "enum", required=True, choices=_enum(ResourceType)),
            Column(
                "resource_code",
                required=True,
                description="Faculty employee ID or room code",
            ),
            DAY,
            Column("start_period", "int", required=True, min_value=1),
            Column("end_period", "int", required=True, min_value=1),
            Column("reason", max_length=255),
        ),
        optional=True,
    ),
    Sheet(
        "GroupBlockedSlots",
        "Periods blocked for a group and all of its batches (e.g. sports).",
        (
            Column("group_code", "ref", required=True, ref_sheet="Groups"),
            DAY,
            Column("period", "int", required=True, min_value=1),
            Column("label", max_length=100),
        ),
        optional=True,
    ),
    Sheet(
        "SessionLocks",
        "Pin a session of an assignment to a day and start period (and optionally a room).",
        (
            Column("subject_code", "ref", required=True, ref_sheet="Subjects"),
            Column("group_code", "ref", required=True, ref_sheet="Groups"),
            Column(
                "faculty_employee_id",
                "ref",
                ref_sheet="Faculty",
                description="Only needed if the subject+group has several assignments",
            ),
            Column("session_number", "int", required=True, min_value=1),
            DAY,
            Column("start_period", "int", required=True, min_value=1),
            Column("room_code", "ref", ref_sheet="Rooms", description="Optional room"),
        ),
        optional=True,
    ),
)

SHEETS_BY_NAME = {sheet.name: sheet for sheet in SHEETS}
INSTRUCTIONS_SHEET = "Instructions"
