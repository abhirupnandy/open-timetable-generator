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


def seed() -> None:
    now = datetime.now(UTC)

    with SessionLocal() as db:
        # ------------------------------------------------------------------
        # Clean existing seed data
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
        courses = [
            Course(
                code="BTECH-CSE",
                name="B.Tech Computer Science and Engineering",
                school_id=school.id,
                duration_years=4,
                total_semesters=8,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Course(
                code="BSC-CS",
                name="B.Sc Computer Science",
                school_id=school.id,
                duration_years=3,
                total_semesters=6,
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
            Course(
                code="MTECH-CSE",
                name="M.Tech Computer Science and Engineering",
                school_id=school.id,
                duration_years=2,
                total_semesters=4,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Course(
                code="MCA",
                name="Master of Computer Applications",
                school_id=school.id,
                duration_years=2,
                total_semesters=4,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Course(
                code="MSC-CS",
                name="M.Sc Computer Science",
                school_id=school.id,
                duration_years=2,
                total_semesters=4,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]

        db.add_all(courses)
        db.flush()

        # ------------------------------------------------------------------
        # Faculty
        #
        # 10 regular faculty
        # 8 PhD scholars, primarily used for laboratory teaching
        # ------------------------------------------------------------------
        faculty = [
            Faculty(
                employee_id="FAC001",
                name="Dr. Ananya Sen",
                email="ananya.sen@example.edu",
                designation=FacultyDesignation.PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="FAC002",
                name="Dr. Rahul Mehta",
                email="rahul.mehta@example.edu",
                designation=FacultyDesignation.ASSOCIATE_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="FAC003",
                name="Dr. Priya Nair",
                email="priya.nair@example.edu",
                designation=FacultyDesignation.ASSOCIATE_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="FAC004",
                name="Dr. Arjun Das",
                email="arjun.das@example.edu",
                designation=FacultyDesignation.ASSISTANT_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="FAC005",
                name="Dr. Sneha Roy",
                email="sneha.roy@example.edu",
                designation=FacultyDesignation.ASSISTANT_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="FAC006",
                name="Dr. Vikram Bose",
                email="vikram.bose@example.edu",
                designation=FacultyDesignation.ASSISTANT_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="FAC007",
                name="Dr. Neha Kapoor",
                email="neha.kapoor@example.edu",
                designation=FacultyDesignation.ASSOCIATE_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="FAC008",
                name="Dr. Rohan Gupta",
                email="rohan.gupta@example.edu",
                designation=FacultyDesignation.ASSISTANT_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="FAC009",
                name="Dr. Meera Iyer",
                email="meera.iyer@example.edu",
                designation=FacultyDesignation.ASSISTANT_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="FAC010",
                name="Dr. Karan Malhotra",
                email="karan.malhotra@example.edu",
                designation=FacultyDesignation.ASSISTANT_PROFESSOR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            # --------------------------------------------------------------
            # PhD scholars
            # --------------------------------------------------------------
            Faculty(
                employee_id="PHD001",
                name="Aditya Sharma",
                email="aditya.sharma@example.edu",
                designation=FacultyDesignation.PHD_SCHOLAR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="PHD002",
                name="Ishita Verma",
                email="ishita.verma@example.edu",
                designation=FacultyDesignation.PHD_SCHOLAR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="PHD003",
                name="Nikhil Singh",
                email="nikhil.singh@example.edu",
                designation=FacultyDesignation.PHD_SCHOLAR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="PHD004",
                name="Pooja Das",
                email="pooja.das@example.edu",
                designation=FacultyDesignation.PHD_SCHOLAR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="PHD005",
                name="Sourav Roy",
                email="sourav.roy@example.edu",
                designation=FacultyDesignation.PHD_SCHOLAR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="PHD006",
                name="Riya Mukherjee",
                email="riya.mukherjee@example.edu",
                designation=FacultyDesignation.PHD_SCHOLAR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="PHD007",
                name="Aman Joshi",
                email="aman.joshi@example.edu",
                designation=FacultyDesignation.PHD_SCHOLAR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Faculty(
                employee_id="PHD008",
                name="Tanvi Rao",
                email="tanvi.rao@example.edu",
                designation=FacultyDesignation.PHD_SCHOLAR,
                school_id=school.id,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]

        db.add_all(faculty)
        db.flush()

        # ------------------------------------------------------------------
        # Rooms
        #
        # 3 lecture halls
        # 8 classrooms
        # 4 laboratories
        # ------------------------------------------------------------------
        rooms = [
            Room(
                code="LH101",
                name="Lecture Hall 101",
                room_type=RoomType.LECTURE_HALL,
                capacity=100,
                school_id=school.id,
                is_shared=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="LH102",
                name="Lecture Hall 102",
                room_type=RoomType.LECTURE_HALL,
                capacity=100,
                school_id=school.id,
                is_shared=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="LH103",
                name="Lecture Hall 103",
                room_type=RoomType.LECTURE_HALL,
                capacity=80,
                school_id=school.id,
                is_shared=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="CR201",
                name="Classroom 201",
                room_type=RoomType.CLASSROOM,
                capacity=60,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="CR202",
                name="Classroom 202",
                room_type=RoomType.CLASSROOM,
                capacity=60,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="CR203",
                name="Classroom 203",
                room_type=RoomType.CLASSROOM,
                capacity=60,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="CR204",
                name="Classroom 204",
                room_type=RoomType.CLASSROOM,
                capacity=60,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="CR205",
                name="Classroom 205",
                room_type=RoomType.CLASSROOM,
                capacity=50,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="CR206",
                name="Classroom 206",
                room_type=RoomType.CLASSROOM,
                capacity=50,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="CR207",
                name="Classroom 207",
                room_type=RoomType.CLASSROOM,
                capacity=50,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="CR208",
                name="Classroom 208",
                room_type=RoomType.CLASSROOM,
                capacity=40,
                school_id=school.id,
                is_shared=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="LAB301",
                name="Computer Lab 301",
                room_type=RoomType.COMPUTER_LAB,
                capacity=30,
                school_id=school.id,
                is_shared=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="LAB302",
                name="Computer Lab 302",
                room_type=RoomType.COMPUTER_LAB,
                capacity=30,
                school_id=school.id,
                is_shared=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="LAB303",
                name="Computer Lab 303",
                room_type=RoomType.COMPUTER_LAB,
                capacity=30,
                school_id=school.id,
                is_shared=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Room(
                code="LAB304",
                name="Computer Lab 304",
                room_type=RoomType.COMPUTER_LAB,
                capacity=30,
                school_id=school.id,
                is_shared=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]

        db.add_all(rooms)
        db.flush()

        # ------------------------------------------------------------------
        # Subjects
        # ------------------------------------------------------------------
        subjects = [
            Subject(
                code="CS101",
                name="Programming Fundamentals",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS102",
                name="Data Structures",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS103",
                name="Database Systems",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS104",
                name="Programming Laboratory",
                subject_type=SubjectType.LAB,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS105",
                name="Computer Networks",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS106",
                name="Software Engineering",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS107",
                name="Operating Systems",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS108",
                name="Operating Systems Laboratory",
                subject_type=SubjectType.LAB,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS109",
                name="Web Technologies",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS110",
                name="Web Technologies Laboratory",
                subject_type=SubjectType.LAB,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS111",
                name="Computer Programming Laboratory",
                subject_type=SubjectType.LAB,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS112",
                name="Artificial Intelligence",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS113",
                name="Machine Learning",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS114",
                name="Research Methodology",
                subject_type=SubjectType.LECTURE,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            Subject(
                code="CS115",
                name="Advanced Programming Laboratory",
                subject_type=SubjectType.LAB,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]

        db.add_all(subjects)
        db.flush()

        # ------------------------------------------------------------------
        # Academic groups
        # ------------------------------------------------------------------

        # B.Tech
        btech_y1_a = AcademicGroup(
            code="BTECH-Y1-A",
            name="B.Tech Year 1 Group A",
            group_type=GroupType.GROUP,
            course_id=courses[0].id,
            capacity=60,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        btech_y1_b = AcademicGroup(
            code="BTECH-Y1-B",
            name="B.Tech Year 1 Group B",
            group_type=GroupType.GROUP,
            course_id=courses[0].id,
            capacity=60,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        btech_y2_a = AcademicGroup(
            code="BTECH-Y2-A",
            name="B.Tech Year 2 Group A",
            group_type=GroupType.GROUP,
            course_id=courses[0].id,
            capacity=60,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        btech_y2_b = AcademicGroup(
            code="BTECH-Y2-B",
            name="B.Tech Year 2 Group B",
            group_type=GroupType.GROUP,
            course_id=courses[0].id,
            capacity=60,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # B.Sc
        bsc_y1 = AcademicGroup(
            code="BSC-Y1",
            name="B.Sc Year 1",
            group_type=GroupType.GROUP,
            course_id=courses[1].id,
            capacity=50,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        bsc_y2 = AcademicGroup(
            code="BSC-Y2",
            name="B.Sc Year 2",
            group_type=GroupType.GROUP,
            course_id=courses[1].id,
            capacity=50,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        bsc_y1_a1 = AcademicGroup(
            code="BSC-Y1-A1",
            name="B.Sc Year 1 Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[1].id,
            parent_group_id=bsc_y1.id,
            capacity=25,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        bsc_y1_a2 = AcademicGroup(
            code="BSC-Y1-A2",
            name="B.Sc Year 1 Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[1].id,
            parent_group_id=bsc_y1.id,
            capacity=25,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        db.add_all([bsc_y1_a1, bsc_y1_a2])
        db.flush()

        bsc_y2_a1 = AcademicGroup(
            code="BSC-Y2-A1",
            name="B.Sc Year 2 Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[1].id,
            parent_group_id=bsc_y2.id,
            capacity=25,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        bsc_y2_a2 = AcademicGroup(
            code="BSC-Y2-A2",
            name="B.Sc Year 2 Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[1].id,
            parent_group_id=bsc_y2.id,
            capacity=25,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        db.add_all([bsc_y2_a1, bsc_y2_a2])
        db.flush()

        # BCA
        bca_y1 = AcademicGroup(
            code="BCA-Y1",
            name="BCA Year 1",
            group_type=GroupType.GROUP,
            course_id=courses[2].id,
            capacity=50,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        bca_y1_a1 = AcademicGroup(
            code="BCA-Y1-A1",
            name="BCA Year 1 Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[2].id,
            parent_group_id=bca_y1.id,
            capacity=25,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        bca_y1_a2 = AcademicGroup(
            code="BCA-Y1-A2",
            name="BCA Year 1 Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[2].id,
            parent_group_id=bca_y1.id,
            capacity=25,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        bca_y2 = AcademicGroup(
            code="BCA-Y2",
            name="BCA Year 2",
            group_type=GroupType.GROUP,
            course_id=courses[2].id,
            capacity=50,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        bca_y2_a1 = AcademicGroup(
            code="BCA-Y2-A1",
            name="BCA Year 2 Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[2].id,
            parent_group_id=bca_y2.id,
            capacity=25,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        bca_y2_a2 = AcademicGroup(
            code="BCA-Y2-A2",
            name="BCA Year 2 Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[2].id,
            parent_group_id=bca_y2.id,
            capacity=25,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        db.add_all([bca_y2_a1, bca_y2_a2])
        db.flush()

        # M.Tech
        mtech_y1 = AcademicGroup(
            code="MTECH-Y1",
            name="M.Tech Year 1",
            group_type=GroupType.GROUP,
            course_id=courses[3].id,
            capacity=35,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        mtech_y1_a1 = AcademicGroup(
            code="MTECH-Y1-A1",
            name="M.Tech Year 1 Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[3].id,
            parent_group_id=mtech_y1.id,
            capacity=18,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        mtech_y1_a2 = AcademicGroup(
            code="MTECH-Y1-A2",
            name="M.Tech Year 1 Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[3].id,
            parent_group_id=mtech_y1.id,
            capacity=17,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # MCA
        mca_y1 = AcademicGroup(
            code="MCA-Y1",
            name="MCA Year 1",
            group_type=GroupType.GROUP,
            course_id=courses[4].id,
            capacity=45,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        mca_y1_a1 = AcademicGroup(
            code="MCA-Y1-A1",
            name="MCA Year 1 Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[4].id,
            parent_group_id=mca_y1.id,
            capacity=23,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        mca_y1_a2 = AcademicGroup(
            code="MCA-Y1-A2",
            name="MCA Year 1 Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[4].id,
            parent_group_id=mca_y1.id,
            capacity=22,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        # M.Sc
        msc_y1 = AcademicGroup(
            code="MSC-Y1",
            name="M.Sc Year 1",
            group_type=GroupType.GROUP,
            course_id=courses[5].id,
            capacity=35,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        msc_y1_a1 = AcademicGroup(
            code="MSC-Y1-A1",
            name="M.Sc Year 1 Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[5].id,
            parent_group_id=msc_y1.id,
            capacity=18,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        msc_y1_a2 = AcademicGroup(
            code="MSC-Y1-A2",
            name="M.Sc Year 1 Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[5].id,
            parent_group_id=msc_y1.id,
            capacity=17,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        db.add_all(
            [
                btech_y1_a,
                btech_y1_b,
                btech_y2_a,
                btech_y2_b,
                bsc_y1,
                bsc_y2,
                bca_y1,
                bca_y1_a1,
                bca_y1_a2,
                bca_y2,
                mtech_y1,
                mtech_y1_a1,
                mtech_y1_a2,
                mca_y1,
                mca_y1_a1,
                mca_y1_a2,
                msc_y1,
                msc_y1_a1,
                msc_y1_a2,
            ]
        )
        db.flush()

        # ------------------------------------------------------------------
        # B.Tech batches
        # ------------------------------------------------------------------
        btech_y2_a1 = AcademicGroup(
            code="BTECH-Y2-A1",
            name="B.Tech Year 2 Group A Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[0].id,
            parent_group_id=btech_y2_a.id,
            capacity=30,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        btech_y2_a2 = AcademicGroup(
            code="BTECH-Y2-A2",
            name="B.Tech Year 2 Group A Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[0].id,
            parent_group_id=btech_y2_a.id,
            capacity=30,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        btech_y2_b1 = AcademicGroup(
            code="BTECH-Y2-B1",
            name="B.Tech Year 2 Group B Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[0].id,
            parent_group_id=btech_y2_b.id,
            capacity=30,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        btech_y2_b2 = AcademicGroup(
            code="BTECH-Y2-B2",
            name="B.Tech Year 2 Group B Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[0].id,
            parent_group_id=btech_y2_b.id,
            capacity=30,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        db.add_all(
            [
                btech_y2_a1,
                btech_y2_a2,
                btech_y2_b1,
                btech_y2_b2,
            ]
        )
        db.flush()

        btech_y1_a1 = AcademicGroup(
            code="BTECH-Y1-A1",
            name="B.Tech Year 1 Group A Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[0].id,
            parent_group_id=btech_y1_a.id,
            capacity=30,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        btech_y1_a2 = AcademicGroup(
            code="BTECH-Y1-A2",
            name="B.Tech Year 1 Group A Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[0].id,
            parent_group_id=btech_y1_a.id,
            capacity=30,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        btech_y1_b1 = AcademicGroup(
            code="BTECH-Y1-B1",
            name="B.Tech Year 1 Group B Batch 1",
            group_type=GroupType.BATCH,
            course_id=courses[0].id,
            parent_group_id=btech_y1_b.id,
            capacity=30,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        btech_y1_b2 = AcademicGroup(
            code="BTECH-Y1-B2",
            name="B.Tech Year 1 Group B Batch 2",
            group_type=GroupType.BATCH,
            course_id=courses[0].id,
            parent_group_id=btech_y1_b.id,
            capacity=30,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        db.add_all(
            [
                btech_y1_a1,
                btech_y1_a2,
                btech_y1_b1,
                btech_y1_b2,
            ]
        )
        db.flush()

        # ------------------------------------------------------------------
        # Teaching assignments
        #
        # Faculty indices:
        # 0-9  = regular faculty
        # 10-17 = PhD scholars
        # ------------------------------------------------------------------
        assignments = [
            # ==============================================================
            # B.Tech Year 1
            # ==============================================================

            # Programming Fundamentals
            TeachingAssignment(
                subject_id=subjects[0].id,
                course_id=courses[0].id,
                academic_group_id=btech_y1_a.id,
                faculty_id=faculty[0].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.LECTURE_HALL.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[0].id,
                course_id=courses[0].id,
                academic_group_id=btech_y1_b.id,
                faculty_id=faculty[0].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.LECTURE_HALL.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),

            # Data Structures
            TeachingAssignment(
                subject_id=subjects[1].id,
                course_id=courses[0].id,
                academic_group_id=btech_y1_a.id,
                faculty_id=faculty[1].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[1].id,
                course_id=courses[0].id,
                academic_group_id=btech_y1_b.id,
                faculty_id=faculty[1].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),

            # Programming Laboratory - 2 x 1 period
            TeachingAssignment(
                subject_id=subjects[3].id,
                course_id=courses[0].id,
                academic_group_id=btech_y1_a1.id,
                faculty_id=faculty[10].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[3].id,
                course_id=courses[0].id,
                academic_group_id=btech_y1_a2.id,
                faculty_id=faculty[11].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[3].id,
                course_id=courses[0].id,
                academic_group_id=btech_y1_b1.id,
                faculty_id=faculty[12].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[3].id,
                course_id=courses[0].id,
                academic_group_id=btech_y1_b2.id,
                faculty_id=faculty[13].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),

            # ==============================================================
            # B.Tech Year 2
            # ==============================================================

            TeachingAssignment(
                subject_id=subjects[0].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_a.id,
                faculty_id=faculty[0].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.LECTURE_HALL.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[0].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_b.id,
                faculty_id=faculty[0].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.LECTURE_HALL.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[2].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_a.id,
                faculty_id=faculty[2].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[2].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_b.id,
                faculty_id=faculty[2].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[4].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_a.id,
                faculty_id=faculty[3].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[4].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_b.id,
                faculty_id=faculty[3].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[6].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_a.id,
                faculty_id=faculty[6].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[6].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_b.id,
                faculty_id=faculty[6].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),

            # OS Laboratory - 1 x 2 periods per batch
            TeachingAssignment(
                subject_id=subjects[7].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_a1.id,
                faculty_id=faculty[14].id,
                sessions_per_week=1,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[7].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_a2.id,
                faculty_id=faculty[15].id,
                sessions_per_week=1,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[7].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_b1.id,
                faculty_id=faculty[16].id,
                sessions_per_week=1,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[7].id,
                course_id=courses[0].id,
                academic_group_id=btech_y2_b2.id,
                faculty_id=faculty[17].id,
                sessions_per_week=1,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),

            # ==============================================================
            # B.Sc
            # ==============================================================

            TeachingAssignment(
                subject_id=subjects[0].id,
                course_id=courses[1].id,
                academic_group_id=bsc_y1.id,
                faculty_id=faculty[7].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[2].id,
                course_id=courses[1].id,
                academic_group_id=bsc_y1.id,
                faculty_id=faculty[2].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[9].id,
                course_id=courses[1].id,
                academic_group_id=bsc_y1_a1.id,
                faculty_id=faculty[16].id,
                sessions_per_week=1,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[9].id,
                course_id=courses[1].id,
                academic_group_id=bsc_y1_a2.id,
                faculty_id=faculty[17].id,
                sessions_per_week=1,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[4].id,
                course_id=courses[1].id,
                academic_group_id=bsc_y2.id,
                faculty_id=faculty[8].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[11].id,
                course_id=courses[1].id,
                academic_group_id=bsc_y2.id,
                faculty_id=faculty[9].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[10].id,
                course_id=courses[1].id,
                academic_group_id=bsc_y2_a1.id,
                faculty_id=faculty[16].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[10].id,
                course_id=courses[1].id,
                academic_group_id=bsc_y2_a2.id,
                faculty_id=faculty[17].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),

            # ==============================================================
            # BCA
            # ==============================================================

            TeachingAssignment(
                subject_id=subjects[0].id,
                course_id=courses[2].id,
                academic_group_id=bca_y1.id,
                faculty_id=faculty[4].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[8].id,
                course_id=courses[2].id,
                academic_group_id=bca_y1.id,
                faculty_id=faculty[5].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[10].id,
                course_id=courses[2].id,
                academic_group_id=bca_y1_a1.id,
                faculty_id=faculty[10].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[10].id,
                course_id=courses[2].id,
                academic_group_id=bca_y1_a2.id,
                faculty_id=faculty[11].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[2].id,
                course_id=courses[2].id,
                academic_group_id=bca_y2.id,
                faculty_id=faculty[2].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[8].id,
                course_id=courses[2].id,
                academic_group_id=bca_y2.id,
                faculty_id=faculty[5].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[9].id,
                course_id=courses[2].id,
                academic_group_id=bca_y2_a1.id,
                faculty_id=faculty[10].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[9].id,
                course_id=courses[2].id,
                academic_group_id=bca_y2_a2.id,
                faculty_id=faculty[11].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),

            # ==============================================================
            # M.Tech
            # ==============================================================

            TeachingAssignment(
                subject_id=subjects[11].id,
                course_id=courses[3].id,
                academic_group_id=mtech_y1.id,
                faculty_id=faculty[0].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[12].id,
                course_id=courses[3].id,
                academic_group_id=mtech_y1.id,
                faculty_id=faculty[7].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[14].id,
                course_id=courses[3].id,
                academic_group_id=mtech_y1_a1.id,
                faculty_id=faculty[12].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[14].id,
                course_id=courses[3].id,
                academic_group_id=mtech_y1_a2.id,
                faculty_id=faculty[13].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),

            # ==============================================================
            # MCA
            # ==============================================================

            TeachingAssignment(
                subject_id=subjects[1].id,
                course_id=courses[4].id,
                academic_group_id=mca_y1.id,
                faculty_id=faculty[1].id,
                sessions_per_week=3,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[3].id,
                course_id=courses[4].id,
                academic_group_id=mca_y1_a1.id,
                faculty_id=faculty[14].id,
                sessions_per_week=1,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[3].id,
                course_id=courses[4].id,
                academic_group_id=mca_y1_a2.id,
                faculty_id=faculty[15].id,
                sessions_per_week=1,
                duration_periods=2,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[5].id,
                course_id=courses[4].id,
                academic_group_id=mca_y1.id,
                faculty_id=faculty[6].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[13].id,
                course_id=courses[4].id,
                academic_group_id=mca_y1.id,
                faculty_id=faculty[9].id,
                sessions_per_week=1,
                duration_periods=1,
                mode=AssignmentMode.EITHER,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),

            # ==============================================================
            # M.Sc
            # ==============================================================

            TeachingAssignment(
                subject_id=subjects[11].id,
                course_id=courses[5].id,
                academic_group_id=msc_y1.id,
                faculty_id=faculty[8].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[12].id,
                course_id=courses[5].id,
                academic_group_id=msc_y1.id,
                faculty_id=faculty[9].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[14].id,
                course_id=courses[5].id,
                academic_group_id=msc_y1_a1.id,
                faculty_id=faculty[16].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[14].id,
                course_id=courses[5].id,
                academic_group_id=msc_y1_a2.id,
                faculty_id=faculty[17].id,
                sessions_per_week=2,
                duration_periods=1,
                mode=AssignmentMode.IN_PERSON,
                required_room_type=RoomType.COMPUTER_LAB.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            TeachingAssignment(
                subject_id=subjects[13].id,
                course_id=courses[5].id,
                academic_group_id=msc_y1.id,
                faculty_id=faculty[7].id,
                sessions_per_week=1,
                duration_periods=1,
                mode=AssignmentMode.EITHER,
                required_room_type=RoomType.CLASSROOM.value,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]

        db.add_all(assignments)
        db.commit()

        print("Seed completed successfully.")
        print(f"Schools: {db.query(School).count()}")
        print(f"Courses: {db.query(Course).count()}")
        print(f"Faculty: {db.query(Faculty).count()}")
        print(f"Rooms: {db.query(Room).count()}")
        print(f"Subjects: {db.query(Subject).count()}")
        print(f"Academic groups: {db.query(AcademicGroup).count()}")
        print(f"Teaching assignments: {db.query(TeachingAssignment).count()}")


if __name__ == "__main__":
    seed()