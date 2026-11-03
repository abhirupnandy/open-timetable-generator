from __future__ import annotations

from dataclasses import dataclass

from app.domain.calendar import Day


@dataclass(frozen=True)
class TimetableViewEntry:
    session_id: str
    day: Day
    start_period: int
    end_period: int
    subject_name: str
    course_code: str
    course_name: str
    academic_group_name: str
    academic_group_code: str
    faculty_name: str
    room_name: str | None
    faculty_code: str = ""
    faculty_designation: str = ""

    @property
    def faculty_key(self) -> str:
        """Stable identifier of the faculty member (employee ID, else name)."""

        return self.faculty_code or self.faculty_name

    @property
    def faculty_label(self) -> str:
        """Name with designation, e.g. "Dr A Rao (Asst. Prof.)"."""

        return faculty_label(self.faculty_name, self.faculty_designation)


DESIGNATION_SHORT = {
    "PROFESSOR": "Prof.",
    "ASSOCIATE_PROFESSOR": "Assoc. Prof.",
    "ASSISTANT_PROFESSOR": "Asst. Prof.",
    "PHD_SCHOLAR": "PhD Scholar",
}


def designation_label(designation: str) -> str:
    return DESIGNATION_SHORT.get(designation, designation.replace("_", " ").title())


def faculty_label(name: str, designation: str) -> str:
    return f"{name} ({designation_label(designation)})" if designation else name


_DAY_ORDER = {
    Day.MONDAY: 0,
    Day.TUESDAY: 1,
    Day.WEDNESDAY: 2,
    Day.THURSDAY: 3,
    Day.FRIDAY: 4,
    Day.SATURDAY: 5,
}


def _entry_sort_key(entry: TimetableViewEntry) -> tuple:
    return (
        _DAY_ORDER[entry.day],
        entry.start_period,
        entry.course_code,
        entry.academic_group_code,
        entry.session_id,
    )


def build_master_view(
    entries: tuple[TimetableViewEntry, ...],
) -> tuple[TimetableViewEntry, ...]:
    """Return all timetable entries in display order."""

    return tuple(sorted(entries, key=_entry_sort_key))


def build_room_views(
    entries: tuple[TimetableViewEntry, ...],
) -> dict[str, tuple[TimetableViewEntry, ...]]:
    """Build one timetable view for each assigned physical room."""

    grouped: dict[str, list[TimetableViewEntry]] = {}

    for entry in entries:
        if entry.room_name is None:
            continue

        grouped.setdefault(entry.room_name, []).append(entry)

    return {
        room_name: tuple(sorted(room_entries, key=_entry_sort_key))
        for room_name, room_entries in sorted(grouped.items())
    }
