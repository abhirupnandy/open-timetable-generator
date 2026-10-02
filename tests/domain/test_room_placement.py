from app.domain.placement import SessionPlacement
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import RoomType, SchedulingRoom
from app.domain.room_placement import is_room_available_for_placement
from app.domain.timetable import Day, SchedulingSession


def make_session() -> SchedulingSession:
    return SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=1,
        faculty_id=1,
        duration_periods=2,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )


def make_room() -> SchedulingRoom:
    return SchedulingRoom(
        id=1,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
    )


def make_placement(
    *,
    day: Day = Day.MONDAY,
    start_period: int = 2,
) -> SessionPlacement:
    return SessionPlacement(
        session=make_session(),
        day=day,
        start_period=start_period,
    )


def make_availability() -> ResourceAvailability:
    return ResourceAvailability(
        resource_id=1,
        windows=(
            __import__("app.domain.availability", fromlist=["AvailabilityWindow"])
            .AvailabilityWindow(
                day=Day.MONDAY,
                start_period=2,
                end_period=5,
            ),
        ),
    )


def test_room_is_available_for_placement():
    room = make_room()
    placement = make_placement()
    availability = make_availability()

    assert is_room_available_for_placement(
        room,
        placement,
        availability,
    ) is True


def test_room_is_unavailable_when_placement_starts_before_window():
    room = make_room()
    placement = make_placement(start_period=1)
    availability = make_availability()

    assert is_room_available_for_placement(
        room,
        placement,
        availability,
    ) is False


def test_room_is_unavailable_when_placement_ends_after_window():
    room = make_room()
    placement = make_placement(start_period=5)
    availability = make_availability()

    assert is_room_available_for_placement(
        room,
        placement,
        availability,
    ) is False


def test_room_is_unavailable_on_different_day():
    room = make_room()
    placement = make_placement(day=Day.TUESDAY)
    availability = make_availability()

    assert is_room_available_for_placement(
        room,
        placement,
        availability,
    ) is False


def test_room_without_availability_is_available():
    room = make_room()
    placement = make_placement()

    assert is_room_available_for_placement(
        room,
        placement,
        None,
    ) is True