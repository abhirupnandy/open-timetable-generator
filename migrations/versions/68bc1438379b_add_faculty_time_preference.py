"""add faculty time preference

Revision ID: 68bc1438379b
Revises: 0001_initial_domain
Create Date: 2026-10-07 18:28:08.696922
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "68bc1438379b"
down_revision: str | Sequence[str] | None = "0001_initial_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("faculty")
    }

    if "time_preference" not in columns:
        op.add_column(
            "faculty",
            sa.Column(
                "time_preference",
                sa.Enum(
                    "ANY",
                    "MORNING",
                    "AFTERNOON",
                    "EVENING",
                    name="facultytimepreference",
                ),
                nullable=False,
                server_default="ANY",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("faculty")
    }

    if "time_preference" in columns:
        op.drop_column(
            "faculty",
            "time_preference",
        )