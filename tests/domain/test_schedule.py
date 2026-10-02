from app.domain.placement import SessionPlacement
from app.domain.room import RoomType, SchedulingRoom
from app.domain.room_assignment import RoomAssignment
from app.domain.schedule import Timetable
from app.domain.timetable import Day, SchedulingSession


def make_placement(session_id: str) -> SessionPlacement:
    session = SchedulingSession(
        id=session_id,
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=1,
        faculty_id=1,
        duration_periods=1,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )

    return SessionPlacement(
        session=session,
        day=Day.MONDAY,
        start_period=1,
    )

def make_room_assignment(session_id: str) -> RoomAssignment:
    placement = make_placement(session_id)
    room = SchedulingRoom(
        id=101,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
    )

    return RoomAssignment(
        placement=placement,
        room=room,
    )


def test_empty_timetable():
    timetable = Timetable.empty()

    assert timetable.placements == ()
    assert timetable.room_assignments == ()
    assert len(timetable) == 0


def test_add_returns_new_timetable():
    timetable = Timetable.empty()
    placement = make_placement("session-1")

    updated = timetable.add(placement)

    assert timetable.placements == ()
    assert updated.placements == (placement,)
    assert len(updated) == 1


def test_multiple_placements():
    first = make_placement("session-1")
    second = make_placement("session-2")

    timetable = (
        Timetable.empty()
        .add(first)
        .add(second)
    )

    assert timetable.placements == (first, second)
    assert len(timetable) == 2


def test_add_room_assignment_returns_new_timetable():
    timetable = Timetable.empty()
    room_assignment = make_room_assignment("session-1")

    updated = timetable.add_room_assignment(room_assignment)

    assert timetable.room_assignments == ()
    assert updated.room_assignments == (room_assignment,)
    assert updated.placements == ()