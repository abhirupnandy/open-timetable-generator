import pytest

from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.room import RoomType, SchedulingRoom
from app.domain.room_assignment import RoomAssignment
from app.domain.timetable import SchedulingSession


def make_session() -> SchedulingSession:
    return SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=10,
        course_id=20,
        academic_group_id=30,
        faculty_id=40,
        duration_periods=2,
        mode="OFFLINE",
        required_room_type="CLASSROOM",
        session_number=1,
    )


def make_placement() -> SessionPlacement:
    return SessionPlacement(
        session=make_session(),
        day=Day.MONDAY,
        start_period=3,
    )


def make_room() -> SchedulingRoom:
    return SchedulingRoom(
        id=101,
        room_type=RoomType.CLASSROOM,
        capacity=60,
    )


def test_room_assignment_stores_placement_and_room() -> None:
    placement = make_placement()
    room = make_room()

    assignment = RoomAssignment(
        placement=placement,
        room=room,
    )

    assert assignment.placement == placement
    assert assignment.room == room


def test_room_assignment_is_immutable() -> None:
    assignment = RoomAssignment(
        placement=make_placement(),
        room=make_room(),
    )

    with pytest.raises(AttributeError):
        assignment.room = make_room()