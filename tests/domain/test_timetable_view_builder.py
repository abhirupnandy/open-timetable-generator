from app.db.models.academic_group import AcademicGroup
from app.db.models.course import Course
from app.db.models.faculty import Faculty
from app.db.models.room import Room
from app.db.models.subject import Subject
from app.db.models.teaching_assignment import TeachingAssignment
from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.room import RoomType, SchedulingRoom
from app.domain.room_assignment import RoomAssignment
from app.domain.schedule import Timetable
from app.domain.timetable import SchedulingSession
from app.domain.timetable_view_builder import build_timetable_view_entries


def test_build_timetable_view_entries(db_session) -> None:
    subject = Subject(
        code="CS101",
        name="Data Structures",
        is_active=True,
    )
    course = Course(
        code="BTECH-CSE",
        name="B.Tech CSE",
        school_id=1,
        duration_years=4,
        total_semesters=8,
        is_active=True,
    )
    group = AcademicGroup(
        code="BTECH-Y1-A",
        name="B.Tech Year 1 Group A",
        group_type="GROUP",
        course_id=course.id,
        capacity=60,
        is_active=True,
    )
    faculty = Faculty(
        employee_id="F001",
        name="Faculty One",
        email="faculty1@example.com",
        designation="ASSISTANT_PROFESSOR",
        school_id=1,
        is_active=True,
    )
    room = Room(
        code="C101",
        name="Classroom 101",
        room_type="CLASSROOM",
        capacity=60,
        school_id=1,
        is_shared=False,
        is_active=True,
    )

    db_session.add_all([subject, course, group, faculty, room])
    db_session.flush()

    assignment = TeachingAssignment(
        subject_id=subject.id,
        course_id=course.id,
        academic_group_id=group.id,
        faculty_id=faculty.id,
        sessions_per_week=1,
        duration_periods=2,
        mode="IN_PERSON",
        is_active=True,
    )
    db_session.add(assignment)
    db_session.flush()

    session = SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=assignment.id,
        subject_id=subject.id,
        course_id=course.id,
        academic_group_id=group.id,
        faculty_id=faculty.id,
        duration_periods=2,
        mode="IN_PERSON",
        required_room_type=None,
        session_number=1,
    )

    placement = SessionPlacement(
        session=session,
        day=Day.MONDAY,
        start_period=2,
    )

    scheduling_room = SchedulingRoom(
        id=room.id,
        room_type=RoomType.CLASSROOM,
        capacity=60,
        is_shared=False,
    )

    timetable = Timetable(
        placements=(placement,),
        room_assignments=(
            RoomAssignment(
                placement=placement,
                room=scheduling_room,
            ),
        ),
    )

    entries = build_timetable_view_entries(
        db_session,
        timetable,
    )

    assert len(entries) == 1

    entry = entries[0]

    assert entry.session_id == session.id
    assert entry.day is Day.MONDAY
    assert entry.start_period == 2
    assert entry.end_period == 3
    assert entry.subject_name == "Data Structures"
    assert entry.course_code == "BTECH-CSE"
    assert entry.course_name == "B.Tech CSE"
    assert entry.academic_group_code == "BTECH-Y1-A"
    assert entry.academic_group_name == "B.Tech Year 1 Group A"
    assert entry.faculty_name == "Faculty One"
    assert entry.room_name == "C101"