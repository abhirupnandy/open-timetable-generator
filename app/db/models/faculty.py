from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.school import School
    from app.db.models.teaching_assignment import TeachingAssignment

class FacultyDesignation(StrEnum):
    ASSISTANT_PROFESSOR = "ASSISTANT_PROFESSOR"
    ASSOCIATE_PROFESSOR = "ASSOCIATE_PROFESSOR"
    PROFESSOR = "PROFESSOR"
    PHD_SCHOLAR = "PHD_SCHOLAR"


class Faculty(Base):
    __tablename__ = "faculty"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    designation: Mapped[FacultyDesignation] = mapped_column(
        SQLEnum(FacultyDesignation), nullable=False
    )
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    school: Mapped[School] = relationship(back_populates="faculty")
    teaching_assignments: Mapped[list[TeachingAssignment]] = relationship(back_populates="faculty")
