from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TimetableRun(Base):
    """One solver run: status, progress log, error details and results."""

    __tablename__ = "timetable_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    session_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    solver_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_weighted_penalty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    log: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    files_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
