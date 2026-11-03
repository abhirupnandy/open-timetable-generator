"""Example rows for the data template.

A small but complete institution: one school, two courses, a group split
into two lab batches, faculty of every designation, and one row on each
optional sheet. Every row is consistent with the others, so the template
imports and solves as-is; replace the rows with your own data.
"""

from __future__ import annotations

EXAMPLE_NOTE = (
    "Yellow rows are EXAMPLES that show what goes in each column. "
    "Overwrite or delete them before importing your own data."
)

EXAMPLE_ROWS: dict[str, list[dict[str, object]]] = {
    "Schools": [
        {"code": "SOET", "name": "School of Engineering and Technology", "is_active": True},
    ],
    "Courses": [
        {
            "code": "BTECH-CSE",
            "name": "B.Tech Computer Science and Engineering",
            "school_code": "SOET",
            "duration_years": 4,
            "total_semesters": 8,
            "is_active": True,
        },
        {
            "code": "MCA",
            "name": "Master of Computer Applications",
            "school_code": "SOET",
            "duration_years": 2,
            "total_semesters": 4,
            "is_active": True,
        },
    ],
    "Faculty": [
        {
            "employee_id": "FAC001",
            "name": "Dr. Meera Iyer",
            "email": "meera.iyer@example.edu",
            "designation": "PROFESSOR",
            "time_preference": "ANY",
            "preferred_day_off": None,
            "school_code": "SOET",
            "is_active": True,
        },
        {
            "employee_id": "FAC002",
            "name": "Dr. Rohan Verma",
            "email": "rohan.verma@example.edu",
            "designation": "ASSOCIATE_PROFESSOR",
            "time_preference": "MORNING",
            "preferred_day_off": "FRIDAY",
            "school_code": "SOET",
            "is_active": True,
        },
        {
            "employee_id": "FAC003",
            "name": "Ms. Kavya Rao",
            "email": "kavya.rao@example.edu",
            "designation": "ASSISTANT_PROFESSOR",
            "time_preference": "AFTERNOON",
            "preferred_day_off": None,
            "school_code": "SOET",
            "is_active": True,
        },
        {
            "employee_id": "PHD001",
            "name": "Arjun Menon",
            "email": "arjun.menon@example.edu",
            "designation": "PHD_SCHOLAR",
            "time_preference": "ANY",
            "preferred_day_off": None,
            "school_code": "SOET",
            "is_active": True,
        },
    ],
    "Rooms": [
        {
            "code": "LH-101",
            "name": "Lecture Hall 101",
            "room_type": "LECTURE_HALL",
            "capacity": 120,
            "school_code": "SOET",
            "is_shared": False,
            "is_active": True,
        },
        {
            "code": "CR-201",
            "name": "Classroom 201",
            "room_type": "CLASSROOM",
            "capacity": 60,
            "school_code": "SOET",
            "is_shared": False,
            "is_active": True,
        },
        {
            "code": "LAB-301",
            "name": "Computer Lab 301",
            "room_type": "COMPUTER_LAB",
            "capacity": 30,
            "school_code": "SOET",
            "is_shared": False,
            "is_active": True,
        },
        {
            "code": "LAB-302",
            "name": "Computer Lab 302 (shared)",
            "room_type": "COMPUTER_LAB",
            "capacity": 30,
            "school_code": "SOET",
            "is_shared": True,
            "is_active": True,
        },
    ],
    "Subjects": [
        {"code": "CS101", "name": "Programming in Python", "subject_type": "LECTURE"},
        {"code": "CS101L", "name": "Python Programming Lab", "subject_type": "LAB"},
        {"code": "MA101", "name": "Engineering Mathematics", "subject_type": "LECTURE"},
        {"code": "MA101T", "name": "Engineering Mathematics Tutorial", "subject_type": "TUTORIAL"},
        {"code": "CA501", "name": "Machine Learning", "subject_type": "LECTURE"},
    ],
    "Groups": [
        {
            "code": "CSE-Y1-A",
            "name": "B.Tech CSE Year 1 Section A",
            "group_type": "GROUP",
            "course_code": "BTECH-CSE",
            "parent_group_code": None,
            "capacity": 60,
        },
        {
            "code": "CSE-Y1-A-B1",
            "name": "B.Tech CSE Year 1 Section A, Batch 1",
            "group_type": "BATCH",
            "course_code": "BTECH-CSE",
            "parent_group_code": "CSE-Y1-A",
            "capacity": 30,
        },
        {
            "code": "CSE-Y1-A-B2",
            "name": "B.Tech CSE Year 1 Section A, Batch 2",
            "group_type": "BATCH",
            "course_code": "BTECH-CSE",
            "parent_group_code": "CSE-Y1-A",
            "capacity": 30,
        },
        {
            "code": "MCA-Y1",
            "name": "MCA Year 1",
            "group_type": "GROUP",
            "course_code": "MCA",
            "parent_group_code": None,
            "capacity": 40,
        },
    ],
    "Assignments": [
        # The whole section attends lectures; each batch has its own lab.
        {
            "subject_code": "CS101",
            "group_code": "CSE-Y1-A",
            "faculty_employee_id": "FAC001",
            "sessions_per_week": 3,
            "duration_periods": 1,
            "mode": "IN_PERSON",
            "required_room_type": "CLASSROOM",
        },
        {
            "subject_code": "MA101",
            "group_code": "CSE-Y1-A",
            "faculty_employee_id": "FAC002",
            "sessions_per_week": 3,
            "duration_periods": 1,
            "mode": "IN_PERSON",
            "required_room_type": "CLASSROOM",
        },
        {
            "subject_code": "MA101T",
            "group_code": "CSE-Y1-A",
            "faculty_employee_id": "FAC003",
            "sessions_per_week": 1,
            "duration_periods": 1,
            "mode": "EITHER",
            "required_room_type": "CLASSROOM",
        },
        {
            "subject_code": "CS101L",
            "group_code": "CSE-Y1-A-B1",
            "faculty_employee_id": "PHD001",
            "sessions_per_week": 1,
            "duration_periods": 2,
            "mode": "IN_PERSON",
            "required_room_type": "COMPUTER_LAB",
        },
        {
            "subject_code": "CS101L",
            "group_code": "CSE-Y1-A-B2",
            "faculty_employee_id": "PHD001",
            "sessions_per_week": 1,
            "duration_periods": 2,
            "mode": "IN_PERSON",
            "required_room_type": "COMPUTER_LAB",
        },
        {
            "subject_code": "CA501",
            "group_code": "MCA-Y1",
            "faculty_employee_id": "FAC001",
            "sessions_per_week": 2,
            "duration_periods": 1,
            "mode": "ONLINE",
            "required_room_type": None,
        },
    ],
    "Unavailability": [
        {
            "resource_type": "FACULTY",
            "resource_code": "FAC002",
            "day": "MONDAY",
            "start_period": 1,
            "end_period": 2,
            "reason": "Department meeting",
        },
        {
            "resource_type": "ROOM",
            "resource_code": "LAB-302",
            "day": "FRIDAY",
            "start_period": 5,
            "end_period": 8,
            "reason": "Booked by another school",
        },
    ],
    "GroupBlockedSlots": [
        {"group_code": "CSE-Y1-A", "day": "WEDNESDAY", "period": 7, "label": "Sports"},
    ],
    "SessionLocks": [
        {
            "subject_code": "CS101",
            "group_code": "CSE-Y1-A",
            "faculty_employee_id": None,
            "session_number": 1,
            "day": "TUESDAY",
            "start_period": 1,
            "room_code": "CR-201",
        },
    ],
}
