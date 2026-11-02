"""add constraint inputs: unavailability, group blocks, locks, lunch/day-off fields

Revision ID: 0003_constraint_inputs
Revises: 68bc1438379b
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_constraint_inputs"
down_revision: str | Sequence[str] | None = "68bc1438379b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WEEKDAYS = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY")


def _weekday() -> sa.Enum:
    return sa.Enum(*WEEKDAYS, name="weekday")


def upgrade() -> None:
    with op.batch_alter_table("teaching_assignments") as batch:
        batch.add_column(sa.Column("allow_across_lunch", sa.Boolean(), nullable=True))

    with op.batch_alter_table("faculty") as batch:
        batch.add_column(sa.Column("preferred_day_off", _weekday(), nullable=True))

    op.create_table(
        "unavailability",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "resource_type",
            sa.Enum("FACULTY", "ROOM", name="resource_type"),
            nullable=False,
        ),
        sa.Column("resource_id", sa.Integer(), nullable=False),
        sa.Column("day", _weekday(), nullable=False),
        sa.Column("start_period", sa.Integer(), nullable=False),
        sa.Column("end_period", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_unavailability_resource_id", "unavailability", ["resource_id"])

    op.create_table(
        "group_blocked_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("academic_group_id", sa.Integer(), nullable=False),
        sa.Column("day", _weekday(), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["academic_group_id"], ["academic_groups.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("academic_group_id", "day", "period"),
    )
    op.create_index(
        "ix_group_blocked_slots_academic_group_id",
        "group_blocked_slots",
        ["academic_group_id"],
    )

    op.create_table(
        "session_locks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("teaching_assignment_id", sa.Integer(), nullable=False),
        sa.Column("session_number", sa.Integer(), nullable=False),
        sa.Column("day", _weekday(), nullable=False),
        sa.Column("start_period", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["teaching_assignment_id"], ["teaching_assignments.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
        sa.UniqueConstraint("teaching_assignment_id", "session_number"),
    )
    op.create_index(
        "ix_session_locks_teaching_assignment_id",
        "session_locks",
        ["teaching_assignment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_session_locks_teaching_assignment_id", table_name="session_locks")
    op.drop_table("session_locks")
    op.drop_index("ix_group_blocked_slots_academic_group_id", table_name="group_blocked_slots")
    op.drop_table("group_blocked_slots")
    op.drop_index("ix_unavailability_resource_id", table_name="unavailability")
    op.drop_table("unavailability")

    with op.batch_alter_table("faculty") as batch:
        batch.drop_column("preferred_day_off")

    with op.batch_alter_table("teaching_assignments") as batch:
        batch.drop_column("allow_across_lunch")
