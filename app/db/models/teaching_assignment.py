from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.academic_group import AcademicGroup
    from app.db.models.course import Course
    from app.db.models.faculty import Faculty
    from app.db.models.subject import Subject

class AssignmentMode(StrEnum):
    IN_PERSON = "IN_PERSON"
    ONLINE = "ONLINE"
    EITHER = "EITHER"


class TeachingAssignment(Base):
    __tablename__ = "teaching_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    academic_group_id: Mapped[int] = mapped_column(
        ForeignKey("academic_groups.id"), nullable=False, index=True
    )
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"), nullable=False, index=True)
    sessions_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_periods: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[AssignmentMode] = mapped_column(SQLEnum(AssignmentMode), nullable=False)
    required_room_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    subject: Mapped[Subject] = relationship(back_populates="teaching_assignments")
    course: Mapped[Course] = relationship(back_populates="teaching_assignments")
    academic_group: Mapped[AcademicGroup] = relationship(back_populates="teaching_assignments")
    faculty: Mapped[Faculty] = relationship(back_populates="teaching_assignments")
