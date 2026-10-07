from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete

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


# ============================================================================
# Seed configuration
# ============================================================================

# Faculty workload policy:
#
# Professor:
#     10 hours total/week INCLUDING 1 hour TREP
#     => maximum 9 teaching hours
#
# Associate Professor:
#     12 hours total/week INCLUDING 1 hour TREP
#     => maximum 11 teaching hours
#
# Assistant Professor:
#     14 hours total/week INCLUDING 1 hour TREP
#     => maximum 13 teaching hours
#
# TREP is NOT represented as a TeachingAssignment because it is an
# institutional faculty event rather than a student-facing class.
#
# Current schema does not yet contain an institutional-event table or a
# faculty availability/rule table. Therefore TREP is documented here and
# should later become a proper hard availability/block constraint.
#
# TREP:
#     Monday, Period 6
#     14:50 - 15:50
#
# The weekly teaching assignments below keep regular faculty teaching loads
# below their respective limits. Laboratory assignments are primarily given
# to PhD scholars.


COURSE_DEFINITIONS = [
    (
        "BTECH-AI",
        "B.Tech Artificial Intelligence",
        4,
        8,
    ),
    (
        "BSC-AI",
        "B.Sc Artificial Intelligence",
        3,
        6,
    ),
    (
        "BCA-AI",
        "Bachelor of Computer Applications - Artificial Intelligence",
        3,
        6,
    ),
    (
        "MTECH-AI",
        "M.Tech Artificial Intelligence",
        2,
        4,
    ),
    (
        "MCA-AI",
        "MCA Artificial Intelligence",
        2,
        4,
    ),
    (
        "MSC-AI",
        "M.Sc Artificial Intelligence",
        2,
        4,
    ),
]


FACULTY_DEFINITIONS = [
    # ------------------------------------------------------------------
    # 4 Professors
    # ------------------------------------------------------------------
    (
        "FAC001",
        "Dr. Ananya Sen",
        "ananya.sen@example.edu",
        FacultyDesignation.PROFESSOR,
    ),
    (
        "FAC002",
        "Dr. Rahul Mehta",
        "rahul.mehta@example.edu",
        FacultyDesignation.PROFESSOR,
    ),
    (
        "FAC003",
        "Dr. Priya Nair",
        "priya.nair@example.edu",
        FacultyDesignation.PROFESSOR,
    ),
    (
        "FAC004",
        "Dr. Arjun Das",
        "arjun.das@example.edu",
        FacultyDesignation.PROFESSOR,
    ),

    # ------------------------------------------------------------------
    # 6 Associate Professors
    # ------------------------------------------------------------------
    (
        "FAC005",
        "Dr. Sneha Roy",
        "sneha.roy@example.edu",
        FacultyDesignation.ASSOCIATE_PROFESSOR,
    ),
    (
        "FAC006",
        "Dr. Vikram Bose",
        "vikram.bose@example.edu",
        FacultyDesignation.ASSOCIATE_PROFESSOR,
    ),
    (
        "FAC007",
        "Dr. Neha Kapoor",
        "neha.kapoor@example.edu",
        FacultyDesignation.ASSOCIATE_PROFESSOR,
    ),
    (
        "FAC008",
        "Dr. Rohan Gupta",
        "rohan.gupta@example.edu",
        FacultyDesignation.ASSOCIATE_PROFESSOR,
    ),
    (
        "FAC009",
        "Dr. Meera Iyer",
        "meera.iyer@example.edu",
        FacultyDesignation.ASSOCIATE_PROFESSOR,
    ),
    (
        "FAC010",
        "Dr. Karan Malhotra",
        "karan.malhotra@example.edu",
        FacultyDesignation.ASSOCIATE_PROFESSOR,
    ),

    # ------------------------------------------------------------------
    # 8 Assistant Professors
    # ------------------------------------------------------------------
    (
        "FAC011",
        "Dr. Ishita Verma",
        "ishita.verma@example.edu",
        FacultyDesignation.ASSISTANT_PROFESSOR,
    ),
    (
        "FAC012",
        "Dr. Nikhil Singh",
        "nikhil.singh@example.edu",
        FacultyDesignation.ASSISTANT_PROFESSOR,
    ),
    (
        "FAC013",
        "Dr. Pooja Das",
        "pooja.das@example.edu",
        FacultyDesignation.ASSISTANT_PROFESSOR,
    ),
    (
        "FAC014",
        "Dr. Sourav Roy",
        "sourav.roy@example.edu",
        FacultyDesignation.ASSISTANT_PROFESSOR,
    ),
    (
        "FAC015",
        "Dr. Riya Mukherjee",
        "riya.mukherjee@example.edu",
        FacultyDesignation.ASSISTANT_PROFESSOR,
    ),
    (
        "FAC016",
        "Dr. Aman Joshi",
        "aman.joshi@example.edu",
        FacultyDesignation.ASSISTANT_PROFESSOR,
    ),
    (
        "FAC017",
        "Dr. Tanvi Rao",
        "tanvi.rao@example.edu",
        FacultyDesignation.ASSISTANT_PROFESSOR,
    ),
    (
        "FAC018",
        "Dr. Kabir Sharma",
        "kabir.sharma@example.edu",
        FacultyDesignation.ASSISTANT_PROFESSOR,
    ),

    # ------------------------------------------------------------------
    # 10 PhD scholars
    # ------------------------------------------------------------------
    (
        "PHD001",
        "Aditya Sharma",
        "aditya.sharma@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
    (
        "PHD002",
        "Ishita Banerjee",
        "ishita.banerjee@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
    (
        "PHD003",
        "Nikhil Verma",
        "nikhil.verma@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
    (
        "PHD004",
        "Pooja Mukherjee",
        "pooja.mukherjee@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
    (
        "PHD005",
        "Sourav Das",
        "sourav.das@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
    (
        "PHD006",
        "Riya Singh",
        "riya.singh@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
    (
        "PHD007",
        "Aman Gupta",
        "aman.gupta@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
    (
        "PHD008",
        "Tanvi Mehta",
        "tanvi.mehta@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
    (
        "PHD009",
        "Kunal Roy",
        "kunal.roy@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
    (
        "PHD010",
        "Madhurima Sen",
        "madhurima.sen@example.edu",
        FacultyDesignation.PHD_SCHOLAR,
    ),
]


ROOM_DEFINITIONS = [
    # ------------------------------------------------------------------
    # 4 lecture halls
    # ------------------------------------------------------------------
    (
        "LH101",
        "Lecture Hall 101",
        RoomType.LECTURE_HALL,
        100,
        True,
    ),
    (
        "LH102",
        "Lecture Hall 102",
        RoomType.LECTURE_HALL,
        100,
        True,
    ),
    (
        "LH103",
        "Lecture Hall 103",
        RoomType.LECTURE_HALL,
        80,
        True,
    ),
    (
        "LH104",
        "Lecture Hall 104",
        RoomType.LECTURE_HALL,
        80,
        True,
    ),

    # ------------------------------------------------------------------
    # 8 teaching classrooms
    # ------------------------------------------------------------------
    (
        "CR201",
        "Classroom 201",
        RoomType.CLASSROOM,
        60,
        False,
    ),
    (
        "CR202",
        "Classroom 202",
        RoomType.CLASSROOM,
        60,
        False,
    ),
    (
        "CR203",
        "Classroom 203",
        RoomType.CLASSROOM,
        60,
        False,
    ),
    (
        "CR204",
        "Classroom 204",
        RoomType.CLASSROOM,
        60,
        False,
    ),
    (
        "CR205",
        "Classroom 205",
        RoomType.CLASSROOM,
        50,
        False,
    ),
    (
        "CR206",
        "Classroom 206",
        RoomType.CLASSROOM,
        50,
        False,
    ),
    (
        "CR207",
        "Classroom 207",
        RoomType.CLASSROOM,
        50,
        False,
    ),
    (
        "CR208",
        "Classroom 208",
        RoomType.CLASSROOM,
        40,
        False,
    ),

    # ------------------------------------------------------------------
    # 4 computer laboratories
    # ------------------------------------------------------------------
    (
        "LAB301",
        "Computer Lab 301",
        RoomType.COMPUTER_LAB,
        30,
        True,
    ),
    (
        "LAB302",
        "Computer Lab 302",
        RoomType.COMPUTER_LAB,
        30,
        True,
    ),
    (
        "LAB303",
        "Computer Lab 303",
        RoomType.COMPUTER_LAB,
        30,
        True,
    ),
    (
        "LAB304",
        "Computer Lab 304",
        RoomType.COMPUTER_LAB,
        30,
        True,
    ),
]


# ============================================================================
# Academic structure
# ============================================================================

# Each entry:
#
#   course code -> years -> (group capacity, batch capacity)
#
# Every academic year has one lecture group and two laboratory batches.
#
# This parent-child structure is important:
#
#     BTECH-Y1-G1
#        ├── BTECH-Y1-G1-B1
#        └── BTECH-Y1-G1-B2
#
# A lecture assigned to the parent group therefore represents all students
# in the two child batches.
#
# This is intentionally populated correctly for every programme so the
# scheduler can later implement student-atom conflicts correctly.

PROGRAMME_YEARS = {
    "BTECH-AI": {
        1: (60, 30),
        2: (60, 30),
        3: (60, 30),
        4: (60, 30),
    },
    "BSC-AI": {
        1: (50, 25),
        2: (50, 25),
        3: (50, 25),
    },
    "BCA-AI": {
        1: (50, 25),
        2: (50, 25),
        3: (50, 25),
    },
    "MTECH-AI": {
        1: (35, 18),
        2: (35, 18),
    },
    "MCA-AI": {
        1: (45, 23),
        2: (45, 23),
    },
    "MSC-AI": {
        1: (35, 18),
        2: (35, 18),
    },
}


# ============================================================================
# Subjects
# ============================================================================

# Format:
#
#     course_code: {
#         year: [
#             (
#                 subject_code,
#                 subject_name,
#                 subject_type,
#                 required_room_type,
#                 sessions_per_week,
#                 duration_periods,
#                 mode,
#             ),
#             ...
#         ]
#     }
#
# Three lecture subjects are assigned to the parent group.
# One laboratory subject is assigned separately to each batch.

SUBJECT_DEFINITIONS = {
    "BTECH-AI": {
        1: [
            (
                "BAI101",
                "Calculus and Linear Algebra",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BAI102",
                "Programming Fundamentals",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BAI103",
                "Digital Electronics",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BAI104L",
                "Programming Fundamentals Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        2: [
            (
                "BAI201",
                "Data Structures",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BAI202",
                "Computer Organization",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BAI203",
                "Probability and Statistics",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BAI204L",
                "Data Structures Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        3: [
            (
                "ABAI2005L",
                "Machine Learning",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "ABAI2009L",
                "Data Management and AI Integration",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "ABAI2011L",
                "Numerical Methods and Optimization Techniques",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                2,
                1,
                AssignmentMode.EITHER,
            ),
            (
                "BAI304L",
                "Machine Learning Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        4: [
            (
                "BAI401",
                "Generative AI",
                SubjectType.LECTURE,
                RoomType.LECTURE_HALL,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BAI402",
                "Computer Vision",
                SubjectType.LECTURE,
                RoomType.LECTURE_HALL,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BAI403",
                "Agentic AI",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.EITHER,
            ),
            (
                "BAI404L",
                "Artificial Intelligence Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
    },

    "BSC-AI": {
        1: [
            (
                "BSC101",
                "Mathematics for Computing",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BSC102",
                "Programming in C",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BSC103",
                "Computer Fundamentals",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BSC104L",
                "Programming Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        2: [
            (
                "BSC201",
                "Data Structures",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BSC202",
                "Algorithms",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BSC203",
                "Computer Networks",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BSC204L",
                "Web Technologies Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        3: [
            (
                "BSC301",
                "Artificial Intelligence",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BSC302",
                "Machine Learning",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BSC303",
                "Data Science and Analytics",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.EITHER,
            ),
            (
                "BSC304L",
                "Data Science Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
    },

    "BCA-AI": {
        1: [
            (
                "BCA101",
                "Programming in C",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BCA102",
                "Mathematics for Computing",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BCA103",
                "Computer Fundamentals",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BCA104L",
                "Programming Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        2: [
            (
                "BCA201",
                "Data Management and AI Integration",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BCA202",
                "Web Technologies",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BCA203",
                "Computer Networks",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BCA204L",
                "Web Technologies Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        3: [
            (
                "BCA301",
                "Software Engineering",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BCA302",
                "Artificial Intelligence",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "BCA303",
                "Machine Learning",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.EITHER,
            ),
            (
                "BCA304L",
                "Advanced Programming Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
    },

    "MTECH-AI": {
        1: [
            (
                "2026AINT601",
                "Signal Theory",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "2026SOAI601",
                "Programming in AI",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "2026MATH601",
                "Mathematics for Computing",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                2,
                1,
                AssignmentMode.EITHER,
            ),
            (
                "AMAI5005L",
                "Advanced Machine Learning Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        2: [
            (
                "MTAI201",
                "Advanced Machine Learning",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "MTAI202",
                "Natural Language Processing",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "MTAI203",
                "Computer Vision",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.EITHER,
            ),
            (
                "MTAI204L",
                "Research Computing Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
    },

    "MCA-AI": {
        1: [
            (
                "2026AINT612",
                "Machine Learning and Pattern Recognition",
                SubjectType.LECTURE,
                RoomType.LECTURE_HALL,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "2026AINT613",
                "Data Science and Analytics",
                SubjectType.LECTURE,
                RoomType.LECTURE_HALL,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "2026MATH611",
                "Mathematics for Computing",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "2026PROG602L",
                "Programming for Artificial Intelligence Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        2: [
            (
                "MCA201",
                "Advanced Data Analytics",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "MCA202",
                "Artificial Intelligence",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "MCA203",
                "Cloud Computing",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.EITHER,
            ),
            (
                "MCA204L",
                "Artificial Intelligence Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
    },

    "MSC-AI": {
        1: [
            (
                "MSCAI101",
                "Artificial Intelligence",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "MSCAI102",
                "Machine Learning",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "MSCAI103",
                "Research Methodology",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                2,
                1,
                AssignmentMode.EITHER,
            ),
            (
                "MSCAI104L",
                "Advanced Programming Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
        2: [
            (
                "MSCAI201",
                "Deep Learning",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "MSCAI202",
                "Natural Language Processing",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.IN_PERSON,
            ),
            (
                "MSCAI203",
                "Computer Vision",
                SubjectType.LECTURE,
                RoomType.CLASSROOM,
                3,
                1,
                AssignmentMode.EITHER,
            ),
            (
                "MSCAI204L",
                "AI Research Laboratory",
                SubjectType.LAB,
                RoomType.COMPUTER_LAB,
                1,
                2,
                AssignmentMode.IN_PERSON,
            ),
        ],
    },
}


# ============================================================================
# Helpers
# ============================================================================


def _make_faculty(
    school_id: int,
    now: datetime,
) -> list[Faculty]:
    return [
        Faculty(
            employee_id=employee_id,
            name=name,
            email=email,
            designation=designation,
            school_id=school_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        for employee_id, name, email, designation in FACULTY_DEFINITIONS
    ]


def _make_rooms(
    school_id: int,
    now: datetime,
) -> list[Room]:
    return [
        Room(
            code=code,
            name=name,
            room_type=room_type,
            capacity=capacity,
            school_id=school_id,
            is_shared=is_shared,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        for code, name, room_type, capacity, is_shared in ROOM_DEFINITIONS
    ]


def _make_courses(
    school_id: int,
    now: datetime,
) -> list[Course]:
    return [
        Course(
            code=code,
            name=name,
            school_id=school_id,
            duration_years=duration_years,
            total_semesters=total_semesters,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        for code, name, duration_years, total_semesters in COURSE_DEFINITIONS
    ]


def _make_academic_groups(
    courses_by_code: dict[str, Course],
    now: datetime,
) -> tuple[
    list[AcademicGroup],
    dict[tuple[str, int], AcademicGroup],
    dict[tuple[str, int, int], AcademicGroup],
]:
    groups: list[AcademicGroup] = []

    for course_code, years in PROGRAMME_YEARS.items():
        course = courses_by_code[course_code]

        for year, (group_capacity, _) in years.items():
            group = AcademicGroup(
                code=f"{course_code}-Y{year}-G1",
                name=f"{course.name} Year {year} Group 1",
                group_type=GroupType.GROUP,
                course_id=course.id,
                capacity=group_capacity,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            groups.append(group)

    return groups, {}, {}


def _make_subjects(
    now: datetime,
) -> list[Subject]:
    subjects: list[Subject] = []

    seen_codes: set[str] = set()

    for course_years in SUBJECT_DEFINITIONS.values():
        for subject_definitions in course_years.values():
            for (
                code,
                name,
                subject_type,
                _room_type,
                _sessions_per_week,
                _duration_periods,
                _mode,
            ) in subject_definitions:
                if code in seen_codes:
                    continue

                seen_codes.add(code)

                subjects.append(
                    Subject(
                        code=code,
                        name=name,
                        subject_type=subject_type,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )

    return subjects


def _make_assignments(
    courses_by_code: dict[str, Course],
    groups_by_key: dict[tuple[str, int], AcademicGroup],
    batches_by_key: dict[tuple[str, int, int], AcademicGroup],
    subjects_by_code: dict[str, Subject],
    faculty: list[Faculty],
    now: datetime,
) -> list[TeachingAssignment]:
    assignments: list[TeachingAssignment] = []

    # First 18 faculty records are regular teaching faculty.
    regular_faculty = faculty[:18]

    # Last 10 faculty records are PhD scholars.
    phd_faculty = faculty[18:]

    regular_index = 0
    phd_index = 0

    for course_code, year_definitions in SUBJECT_DEFINITIONS.items():
        course = courses_by_code[course_code]

        for year, subject_definitions in year_definitions.items():
            group = groups_by_key[(course_code, year)]

            for (
                subject_code,
                _subject_name,
                subject_type,
                room_type,
                sessions_per_week,
                duration_periods,
                mode,
            ) in subject_definitions:
                subject = subjects_by_code[subject_code]

                if subject_type == SubjectType.LAB:
                    # Each lab is offered separately to both batches.
                    for batch_number in (1, 2):
                        batch = batches_by_key[(course_code, year, batch_number)]

                        assigned_faculty = phd_faculty[phd_index % len(phd_faculty)]
                        phd_index += 1

                        assignments.append(
                            TeachingAssignment(
                                subject_id=subject.id,
                                course_id=course.id,
                                academic_group_id=batch.id,
                                faculty_id=assigned_faculty.id,
                                sessions_per_week=sessions_per_week,
                                duration_periods=duration_periods,
                                mode=mode,
                                required_room_type=room_type.value,
                                is_active=True,
                                created_at=now,
                                updated_at=now,
                            )
                        )

                    continue

                # Lecture/tutorial assignment goes to the parent group.
                assigned_faculty = regular_faculty[regular_index % len(regular_faculty)]
                regular_index += 1

                assignments.append(
                    TeachingAssignment(
                        subject_id=subject.id,
                        course_id=course.id,
                        academic_group_id=group.id,
                        faculty_id=assigned_faculty.id,
                        sessions_per_week=sessions_per_week,
                        duration_periods=duration_periods,
                        mode=mode,
                        required_room_type=room_type.value,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )

    return assignments


# ============================================================================
# Main seed
# ============================================================================


def seed() -> None:
    now = datetime.now(UTC)

    with SessionLocal() as db:
        # ------------------------------------------------------------------
        # Remove previous seed data.
        #
        # TeachingAssignment must be deleted before AcademicGroup.
        # AcademicGroup must be deleted before Course.
        # ------------------------------------------------------------------
        db.execute(delete(TeachingAssignment))
        db.execute(delete(AcademicGroup))
        db.execute(delete(Subject))
        db.execute(delete(Room))
        db.execute(delete(Faculty))
        db.execute(delete(Course))
        db.execute(delete(School))

        # ------------------------------------------------------------------
        # School
        # ------------------------------------------------------------------
        school = School(
            code="SCI-TECH",
            name="School of Science and Technology",
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        db.add(school)
        db.flush()

        # ------------------------------------------------------------------
        # Courses
        # ------------------------------------------------------------------
        courses = _make_courses(school.id, now)

        db.add_all(courses)
        db.flush()

        courses_by_code = {course.code: course for course in courses}

        # ------------------------------------------------------------------
        # Faculty
        #
        # 18 regular faculty:
        #     4 Professors
        #     6 Associate Professors
        #     8 Assistant Professors
        #
        # 10 PhD scholars.
        # ------------------------------------------------------------------
        faculty = _make_faculty(school.id, now)

        db.add_all(faculty)
        db.flush()

        # ------------------------------------------------------------------
        # Rooms
        #
        # 12 teaching rooms:
        #     4 lecture halls
        #     8 classrooms
        #
        # 4 computer laboratories.
        # ------------------------------------------------------------------
        rooms = _make_rooms(school.id, now)

        db.add_all(rooms)
        db.flush()

        # ------------------------------------------------------------------
        # Subjects
        # ------------------------------------------------------------------
        subjects = _make_subjects(now)

        db.add_all(subjects)
        db.flush()

        subjects_by_code = {subject.code: subject for subject in subjects}

        # ------------------------------------------------------------------
        # Academic groups
        #
        # Create parent groups first so that every batch can reference its
        # parent_group_id correctly.
        # ------------------------------------------------------------------
        groups_by_key: dict[tuple[str, int], AcademicGroup] = {}

        for course_code, years in PROGRAMME_YEARS.items():
            course = courses_by_code[course_code]

            for year, (group_capacity, batch_capacity) in years.items():
                group = AcademicGroup(
                    code=f"{course_code}-Y{year}-G1",
                    name=f"{course.name} Year {year} Group 1",
                    group_type=GroupType.GROUP,
                    course_id=course.id,
                    capacity=group_capacity,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )

                db.add(group)
                groups_by_key[(course_code, year)] = group

        db.flush()

        # ------------------------------------------------------------------
        # Batches
        #
        # Every batch has a parent group.
        # ------------------------------------------------------------------
        batches_by_key: dict[tuple[str, int, int], AcademicGroup] = {}

        for course_code, years in PROGRAMME_YEARS.items():
            course = courses_by_code[course_code]

            for year, (_group_capacity, batch_capacity) in years.items():
                parent_group = groups_by_key[(course_code, year)]

                for batch_number in (1, 2):
                    batch = AcademicGroup(
                        code=(
                            f"{course_code}-Y{year}-G1-"
                            f"B{batch_number}"
                        ),
                        name=(
                            f"{course.name} Year {year} "
                            f"Group 1 Batch {batch_number}"
                        ),
                        group_type=GroupType.BATCH,
                        course_id=course.id,
                        parent_group_id=parent_group.id,
                        capacity=batch_capacity,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )

                    db.add(batch)
                    batches_by_key[
                        (course_code, year, batch_number)
                    ] = batch

        db.flush()

        # ------------------------------------------------------------------
        # Teaching assignments
        # ------------------------------------------------------------------
        assignments = _make_assignments(
            courses_by_code=courses_by_code,
            groups_by_key=groups_by_key,
            batches_by_key=batches_by_key,
            subjects_by_code=subjects_by_code,
            faculty=faculty,
            now=now,
        )

        db.add_all(assignments)

        # ------------------------------------------------------------------
        # Commit
        # ------------------------------------------------------------------
        db.commit()

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        print("=" * 70)
        print("Large timetable seed completed successfully.")
        print("=" * 70)

        print(f"Schools:             {db.query(School).count()}")
        print(f"Courses:             {db.query(Course).count()}")
        print(f"Faculty:             {db.query(Faculty).count()}")
        print(f"  Regular faculty:  18")
        print(f"  PhD scholars:     10")
        print(f"Rooms:               {db.query(Room).count()}")
        print(f"  Teaching rooms:   12")
        print(f"  Computer labs:     4")
        print(f"Subjects:            {db.query(Subject).count()}")
        print(f"Academic groups:     {db.query(AcademicGroup).count()}")
        print(f"Teaching assignments:{db.query(TeachingAssignment).count()}")

        print()
        print("Faculty workload policy:")
        print("  Professor:          10 hours total including 1 TREP hour")
        print("  Associate Professor:12 hours total including 1 TREP hour")
        print("  Assistant Professor:14 hours total including 1 TREP hour")

        print()
        print("TREP:")
        print("  Monday / Period 6 / 14:50-15:50")
        print("  Institutional faculty activity; not a TeachingAssignment")

        print()
        print("Academic hierarchy:")
        print("  Every programme-year group has two child laboratory batches.")

        print("=" * 70)


if __name__ == "__main__":
    seed()