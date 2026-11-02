from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Weekday(StrEnum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"


class ResourceType(StrEnum):
    FACULTY = "FACULTY"
    ROOM = "ROOM"


class Unavailability(Base):
    """A period range in which a faculty member or room cannot be scheduled.

    Shared rooms record their external bookings here as ROOM unavailability.
    """

    __tablename__ = "unavailability"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_type: Mapped[ResourceType] = mapped_column(
        SQLEnum(ResourceType, name="resource_type"), nullable=False
    )
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    day: Mapped[Weekday] = mapped_column(SQLEnum(Weekday, name="weekday"), nullable=False)
    start_period: Mapped[int] = mapped_column(Integer, nullable=False)
    end_period: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GroupBlockedSlot(Base):
    """A period blocked for an academic group and all of its descendants."""

    __tablename__ = "group_blocked_slots"
    __table_args__ = (UniqueConstraint("academic_group_id", "day", "period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_group_id: Mapped[int] = mapped_column(
        ForeignKey("academic_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day: Mapped[Weekday] = mapped_column(SQLEnum(Weekday, name="weekday"), nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SessionLock(Base):
    """Pins one session of a teaching assignment to a day/start period (and room)."""

    __tablename__ = "session_locks"
    __table_args__ = (UniqueConstraint("teaching_assignment_id", "session_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teaching_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("teaching_assignments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)
    day: Mapped[Weekday] = mapped_column(SQLEnum(Weekday, name="weekday"), nullable=False)
    start_period: Mapped[int] = mapped_column(Integer, nullable=False)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
