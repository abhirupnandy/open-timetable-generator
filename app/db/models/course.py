from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.academic_group import AcademicGroup
    from app.db.models.school import School
    from app.db.models.teaching_assignment import TeachingAssignment

class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    duration_years: Mapped[int] = mapped_column(Integer, nullable=False)
    total_semesters: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    school: Mapped[School] = relationship(back_populates="courses")
    academic_groups: Mapped[list[AcademicGroup]] = relationship(back_populates="course")
    teaching_assignments: Mapped[list[TeachingAssignment]] = relationship(back_populates="course")
