"""persist timetable runs with logs and errors

Revision ID: 0004_timetable_runs
Revises: 0003_constraint_inputs
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_timetable_runs"
down_revision: str | Sequence[str] | None = "0003_constraint_inputs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "timetable_runs",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("stage", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("elapsed_seconds", sa.Float(), nullable=False),
        sa.Column("max_time_seconds", sa.Float(), nullable=False),
        sa.Column("session_count", sa.Integer(), nullable=False),
        sa.Column("solver_status", sa.String(length=20), nullable=True),
        sa.Column("total_weighted_penalty", sa.Integer(), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("log", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("files_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_timetable_runs_status", "timetable_runs", ["status"])
    op.create_index("ix_timetable_runs_started_at", "timetable_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_timetable_runs_started_at", table_name="timetable_runs")
    op.drop_index("ix_timetable_runs_status", table_name="timetable_runs")
    op.drop_table("timetable_runs")
