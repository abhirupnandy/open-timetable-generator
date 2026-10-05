from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AcademicGroup, Course, Faculty, Room, Subject


def load_render_metadata(
    db: Session,
) -> tuple[
    dict[int, str],
    dict[int, tuple[str, str]],
    dict[int, str],
    dict[int, str],
    dict[int, tuple[str, str]],
]:
    """Load human-readable metadata for timetable rendering."""

    subjects = tuple(
        db.scalars(
            select(Subject).where(
                Subject.is_active.is_(True)
            )
        ).all()
    )

    groups = tuple(
        db.scalars(
            select(AcademicGroup).where(
                AcademicGroup.is_active.is_(True)
            )
        ).all()
    )

    faculty = tuple(
        db.scalars(
            select(Faculty).where(
                Faculty.is_active.is_(True)
            )
        ).all()
    )

    rooms = tuple(
        db.scalars(
            select(Room).where(
                Room.is_active.is_(True)
            )
        ).all()
    )

    courses = tuple(
        db.scalars(
            select(Course).where(
                Course.is_active.is_(True)
            )
        ).all()
    )

    subject_names = {
        subject.id: subject.name
        for subject in subjects
    }

    group_metadata = {
        group.id: (group.code, group.name)
        for group in groups
    }

    faculty_names = {
        member.id: member.name
        for member in faculty
    }

    room_names = {
        room.id: room.code
        for room in rooms
    }

    course_metadata = {
        course.id: (course.code, course.name)
        for course in courses
    }

    return (
        subject_names,
        group_metadata,
        faculty_names,
        room_names,
        course_metadata,
    )