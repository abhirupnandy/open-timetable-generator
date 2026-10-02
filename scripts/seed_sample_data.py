import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.models import (
    AcademicGroup,
    AssignmentMode,
    Course,
    Faculty,
    FacultyDesignation,
    GroupType,
    Room,
    RoomType,
    School,
    Subject,
    SubjectType,
    TeachingAssignment,
)
from app.db.session import SessionLocal


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(School).where(School.code == "SAI")):
            print("Sample data already exists; nothing to do.")
            return
        now = datetime.now(UTC)
        school = School(
            code="SAI", name="School of AI", is_active=True, created_at=now, updated_at=now
        )
        db.add(school)
        db.flush()
        courses = [
            Course(
                code="BTECH-AI",
                name="B.Tech Artificial Intelligence",
                school_id=school.id,
                duration_years=4,
                total_semesters=8,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Course(
                code="BCA",
                name="Bachelor of Computer Applications",
                school_id=school.id,
                duration_years=3,
                total_semesters=6,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(courses)
        db.flush()
        faculty = [
            Faculty(
                employee_id="F001",
                name="Anita Sharma",
                email="anita.sharma@example.edu",
                designation=FacultyDesignation.PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="F002",
                name="Rahul Mehta",
                email="rahul.mehta@example.edu",
                designation=FacultyDesignation.ASSOCIATE_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="F003",
                name="Neha Kapoor",
                email="neha.kapoor@example.edu",
                designation=FacultyDesignation.ASSISTANT_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="F004",
                name="Vikram Singh",
                email="vikram.singh@example.edu",
                designation=FacultyDesignation.PHD_SCHOLAR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(faculty)
        db.flush()
        rooms = [
            Room(
                code="LH-01",
                name="Lecture Hall 01",
                room_type=RoomType.LECTURE_HALL,
                capacity=120,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="LH-02",
                name="Lecture Hall 02",
                room_type=RoomType.LECTURE_HALL,
                capacity=120,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="CL-01",
                name="Computer Lab 01",
                room_type=RoomType.COMPUTER_LAB,
                capacity=60,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="SL-01",
                name="Special Lab 01",
                room_type=RoomType.SPECIAL_LAB,
                capacity=30,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(rooms)
        db.flush()
        subjects = [
            Subject(
                code="DATA-STRUCTURES",
                name="Data Structures",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="DATABASE-SYSTEMS",
                name="Database Systems",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="COMPUTER-NETWORKS",
                name="Computer Networks",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="PROGRAMMING-LAB",
                name="Programming Lab",
                subject_type=SubjectType.LAB,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(subjects)
        db.flush()
        groups = [
            AcademicGroup(
                code="BTECH-AI-Y1-G1",
                name="B.Tech AI Year 1 Group 1",
                group_type=GroupType.GROUP,
                course_id=courses[0].id,
                capacity=60,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            AcademicGroup(
                code="BTECH-AI-Y1-G2",
                name="B.Tech AI Year 1 Group 2",
                group_type=GroupType.GROUP,
                course_id=courses[0].id,
                capacity=60,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(groups)
        db.flush()
        batches = [
            AcademicGroup(
                code="BTECH-AI-Y1-G1-B1",
                name="B.Tech AI Year 1 Group 1 Batch 1",
                group_type=GroupType.BATCH,
                course_id=courses[0].id,
                parent_group_id=groups[0].id,
                capacity=30,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            AcademicGroup(
                code="BTECH-AI-Y1-G1-B2",
                name="B.Tech AI Year 1 Group 1 Batch 2",
                group_type=GroupType.BATCH,
                course_id=courses[0].id,
                parent_group_id=groups[0].id,
                capacity=30,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(batches)
        db.flush()
        assignments = [
            TeachingAssignment(
                subject_id=subjects[0].id,
                course_id=courses[0].id,
                academic_group_id=groups[0].id,
                faculty_id=faculty[0].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.LECTURE_HALL,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[0].id,
                course_id=courses[0].id,
                academic_group_id=groups[1].id,
                faculty_id=faculty[1].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.LECTURE_HALL,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[3].id,
                course_id=courses[0].id,
                academic_group_id=batches[0].id,
                faculty_id=faculty[2].id,
                sessions_per_week=2,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[3].id,
                course_id=courses[0].id,
                academic_group_id=batches[1].id,
                faculty_id=faculty[3].id,
                sessions_per_week=2,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        db.add_all(assignments)
        db.commit()
        print("Sample data seeded successfully.")


if __name__ == "__main__":
    seed()
