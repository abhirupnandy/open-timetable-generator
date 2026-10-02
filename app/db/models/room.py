from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.school import School

class RoomType(StrEnum):
    LECTURE_HALL = "LECTURE_HALL"
    COMPUTER_LAB = "COMPUTER_LAB"
    SPECIAL_LAB = "SPECIAL_LAB"
    CLASSROOM = "CLASSROOM"


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    room_type: Mapped[RoomType] = mapped_column(SQLEnum(RoomType), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False, index=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    school: Mapped[School] = relationship(back_populates="rooms")
