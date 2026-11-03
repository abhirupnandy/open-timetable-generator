"""user accounts for login and role-based access

Revision ID: 0005_users
Revises: 0004_timetable_runs
Create Date: 2026-11-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_users"
down_revision: str | Sequence[str] | None = "0004_timetable_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False, server_default=""),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "COORDINATOR", "FACULTY", name="userrole"),
            nullable=False,
        ),
        sa.Column("faculty_employee_id", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_faculty_employee_id", "users", ["faculty_employee_id"])


def downgrade() -> None:
    op.drop_index("ix_users_faculty_employee_id", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
