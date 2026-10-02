"""create initial timetable domain tables

Revision ID: 0001_initial_domain
Revises:
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_domain"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_schools_code", "schools", ["code"], unique=False)

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("duration_years", sa.Integer(), nullable=False),
        sa.Column("total_semesters", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_courses_code", "courses", ["code"], unique=False)
    op.create_index("ix_courses_school_id", "courses", ["school_id"], unique=False)

    op.create_table(
        "faculty",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "designation",
            sa.Enum(
                "ASSISTANT_PROFESSOR",
                "ASSOCIATE_PROFESSOR",
                "PROFESSOR",
                "PHD_SCHOLAR",
                name="faculty_designation",
            ),
            nullable=False,
        ),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.UniqueConstraint("employee_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_faculty_employee_id", "faculty", ["employee_id"], unique=False)
    op.create_index("ix_faculty_school_id", "faculty", ["school_id"], unique=False)

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column(
            "room_type",
            sa.Enum("LECTURE_HALL", "COMPUTER_LAB", "SPECIAL_LAB", "CLASSROOM", name="room_type"),
            nullable=False,
        ),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_rooms_code", "rooms", ["code"], unique=False)
    op.create_index("ix_rooms_school_id", "rooms", ["school_id"], unique=False)

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column(
            "subject_type",
            sa.Enum("LECTURE", "LAB", "TUTORIAL", name="subject_type"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_subjects_code", "subjects", ["code"], unique=False)

    op.create_table(
        "academic_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("group_type", sa.Enum("GROUP", "BATCH", name="group_type"), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("parent_group_id", sa.Integer(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["parent_group_id"], ["academic_groups.id"]),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_academic_groups_code", "academic_groups", ["code"], unique=False)
    op.create_index("ix_academic_groups_course_id", "academic_groups", ["course_id"], unique=False)
    op.create_index(
        "ix_academic_groups_parent_group_id", "academic_groups", ["parent_group_id"], unique=False
    )

    op.create_table(
        "teaching_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("academic_group_id", sa.Integer(), nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=False),
        sa.Column("sessions_per_week", sa.Integer(), nullable=False),
        sa.Column("duration_periods", sa.Integer(), nullable=False),
        sa.Column(
            "mode", sa.Enum("IN_PERSON", "ONLINE", "EITHER", name="assignment_mode"), nullable=False
        ),
        sa.Column("required_room_type", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.ForeignKeyConstraint(["academic_group_id"], ["academic_groups.id"]),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"]),
    )
    for column in ("subject_id", "course_id", "academic_group_id", "faculty_id"):
        op.create_index(
            f"ix_teaching_assignments_{column}", "teaching_assignments", [column], unique=False
        )


def downgrade() -> None:
    op.drop_table("teaching_assignments")
    op.drop_index("ix_academic_groups_parent_group_id", table_name="academic_groups")
    op.drop_index("ix_academic_groups_course_id", table_name="academic_groups")
    op.drop_index("ix_academic_groups_code", table_name="academic_groups")
    op.drop_table("academic_groups")
    op.drop_index("ix_subjects_code", table_name="subjects")
    op.drop_table("subjects")
    op.drop_index("ix_rooms_school_id", table_name="rooms")
    op.drop_index("ix_rooms_code", table_name="rooms")
    op.drop_table("rooms")
    op.drop_index("ix_faculty_school_id", table_name="faculty")
    op.drop_index("ix_faculty_employee_id", table_name="faculty")
    op.drop_table("faculty")
    op.drop_index("ix_courses_school_id", table_name="courses")
    op.drop_index("ix_courses_code", table_name="courses")
    op.drop_table("courses")
    op.drop_index("ix_schools_code", table_name="schools")
    op.drop_table("schools")
