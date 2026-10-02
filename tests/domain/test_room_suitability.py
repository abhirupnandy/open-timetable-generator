from app.domain.room import RoomType, SchedulingRoom
from app.domain.room_suitability import is_room_suitable
from app.domain.timetable import Day, SchedulingSession, TimetableInput


def make_session(
    *,
    mode: str = "IN_PERSON",
    required_room_type: str | None = "LECTURE_HALL",
) -> SchedulingSession:
    return SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=1,
        faculty_id=1,
        duration_periods=1,
        mode=mode,
        required_room_type=required_room_type,
        session_number=1,
    )


def make_timetable_input(
    session: SchedulingSession,
    *,
    group_capacity: int = 60,
) -> TimetableInput:
    return TimetableInput(
        days=(Day.MONDAY,),
        periods_per_day=4,
        sessions=(session,),
        academic_group_capacities={
            session.academic_group_id: group_capacity,
        },
    )


def test_room_is_suitable_when_type_and_capacity_match():
    session = make_session()
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
    )
    timetable_input = make_timetable_input(session)

    assert is_room_suitable(
        session,
        room,
        timetable_input,
    ) is True


def test_room_is_not_suitable_when_type_does_not_match():
    session = make_session()
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.COMPUTER_LAB,
        capacity=60,
    )
    timetable_input = make_timetable_input(session)

    assert is_room_suitable(
        session,
        room,
        timetable_input,
    ) is False


def test_room_is_not_suitable_when_capacity_is_insufficient():
    session = make_session()
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.LECTURE_HALL,
        capacity=40,
    )
    timetable_input = make_timetable_input(
        session,
        group_capacity=60,
    )

    assert is_room_suitable(
        session,
        room,
        timetable_input,
    ) is False


def test_room_is_suitable_when_capacity_is_sufficient():
    session = make_session()
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
    )
    timetable_input = make_timetable_input(
        session,
        group_capacity=50,
    )

    assert is_room_suitable(
        session,
        room,
        timetable_input,
    ) is True


def test_online_session_does_not_require_a_room():
    session = make_session(
        mode="ONLINE",
        required_room_type=None,
    )
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
    )
    timetable_input = make_timetable_input(session)

    assert is_room_suitable(
        session,
        room,
        timetable_input,
    ) is False


def test_session_without_required_room_type_accepts_suitable_physical_room():
    session = make_session(required_room_type=None)
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.CLASSROOM,
        capacity=60,
    )
    timetable_input = make_timetable_input(session)

    assert is_room_suitable(
        session,
        room,
        timetable_input,
    ) is True