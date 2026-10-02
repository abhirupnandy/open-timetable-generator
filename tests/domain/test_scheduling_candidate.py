from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.room import RoomType, SchedulingRoom
from app.domain.scheduling_candidate import SchedulingCandidate
from app.domain.timetable import SchedulingSession


def test_scheduling_candidate_binds_placement_and_room():
    session = SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=10,
        course_id=20,
        academic_group_id=30,
        faculty_id=40,
        duration_periods=2,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )

    placement = SessionPlacement(
        session=session,
        day=Day.MONDAY,
        start_period=2,
    )

    room = SchedulingRoom(
        id=101,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
    )

    candidate = SchedulingCandidate(
        placement=placement,
        room=room,
    )

    assert candidate.placement == placement
    assert candidate.room == room


def test_scheduling_candidate_can_have_no_room():
    session = SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=10,
        course_id=20,
        academic_group_id=30,
        faculty_id=40,
        duration_periods=2,
        mode="ONLINE",
        required_room_type=None,
        session_number=1,
    )

    placement = SessionPlacement(
        session=session,
        day=Day.MONDAY,
        start_period=2,
    )

    candidate = SchedulingCandidate(
        placement=placement,
        room=None,
    )

    assert candidate.placement == placement
    assert candidate.room is None