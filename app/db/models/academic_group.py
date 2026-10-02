from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.course import Course
    from app.db.models.teaching_assignment import TeachingAssignment

class GroupType(StrEnum):
    GROUP = "GROUP"
    BATCH = "BATCH"


class AcademicGroup(Base):
    __tablename__ = "academic_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    group_type: Mapped[GroupType] = mapped_column(SQLEnum(GroupType), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    parent_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("academic_groups.id"), nullable=True, index=True
    )
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    course: Mapped[Course] = relationship(back_populates="academic_groups")
    parent_group: Mapped[AcademicGroup | None] = relationship(
        back_populates="child_groups", remote_side="AcademicGroup.id"
    )
    child_groups: Mapped[list[AcademicGroup]] = relationship(back_populates="parent_group")
    teaching_assignments: Mapped[list[TeachingAssignment]] = relationship(
        back_populates="academic_group"
    )
