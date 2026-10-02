from app.domain.availability import AvailabilityWindow
from app.domain.placement import SessionPlacement
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import RoomType, SchedulingRoom
from app.domain.room_candidates import candidate_rooms, candidate_rooms_for_placement
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


def test_candidate_rooms_includes_suitable_room():
    session = make_session()
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
    )
    timetable_input = make_timetable_input(session)

    result = candidate_rooms(
        session,
        [room],
        timetable_input,
    )

    assert result == (room,)


def test_candidate_rooms_excludes_wrong_room_type():
    session = make_session()
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.COMPUTER_LAB,
        capacity=60,
    )
    timetable_input = make_timetable_input(session)

    result = candidate_rooms(
        session,
        [room],
        timetable_input,
    )

    assert result == ()


def test_candidate_rooms_excludes_insufficient_capacity():
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

    result = candidate_rooms(
        session,
        [room],
        timetable_input,
    )

    assert result == ()


def test_candidate_rooms_returns_multiple_suitable_rooms():
    session = make_session()
    rooms = (
        SchedulingRoom(
            id=1,
            room_type=RoomType.LECTURE_HALL,
            capacity=60,
        ),
        SchedulingRoom(
            id=2,
            room_type=RoomType.LECTURE_HALL,
            capacity=100,
        ),
    )
    timetable_input = make_timetable_input(session)

    result = candidate_rooms(
        session,
        rooms,
        timetable_input,
    )

    assert result == rooms


def test_candidate_rooms_returns_no_rooms_for_online_session():
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

    result = candidate_rooms(
        session,
        [room],
        timetable_input,
    )

    assert result == ()


def test_candidate_rooms_for_placement_includes_available_suitable_room():
    session = make_session()
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
    )
    timetable_input = make_timetable_input(session)
    timetable_input = TimetableInput(
        days=timetable_input.days,
        periods_per_day=timetable_input.periods_per_day,
        sessions=timetable_input.sessions,
        academic_group_capacities=timetable_input.academic_group_capacities,
        room_availability={
            room.id: ResourceAvailability(
                resource_id=room.id,
                windows=(
                    AvailabilityWindow(
                        day=Day.MONDAY,
                        start_period=1,
                        end_period=4,
                    ),
                ),
            ),
        },
    )

    placement = SessionPlacement(
        session=session,
        day=Day.MONDAY,
        start_period=2,
    )

    result = candidate_rooms_for_placement(
        placement,
        (room,),
        timetable_input,
    )

    assert result == (room,)


def test_candidate_rooms_for_placement_excludes_unavailable_room():
    session = make_session()
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.LECTURE_HALL,
        capacity=60,
    )
    timetable_input = TimetableInput(
        days=(Day.MONDAY,),
        periods_per_day=4,
        sessions=(session,),
        academic_group_capacities={
            session.academic_group_id: 60,
        },
        room_availability={
            room.id: ResourceAvailability(
                resource_id=room.id,
                windows=(
                    AvailabilityWindow(
                        day=Day.MONDAY,
                        start_period=1,
                        end_period=1,
                    ),
                ),
            ),
        },
    )

    placement = SessionPlacement(
        session=session,
        day=Day.MONDAY,
        start_period=2,
    )

    result = candidate_rooms_for_placement(
        placement,
        (room,),
        timetable_input,
    )

    assert result == ()



def test_candidate_rooms_for_placement_excludes_unsuitable_room_even_if_available():
    session = make_session()
    room = SchedulingRoom(
        id=1,
        room_type=RoomType.COMPUTER_LAB,
        capacity=60,
    )
    timetable_input = TimetableInput(
        days=(Day.MONDAY,),
        periods_per_day=4,
        sessions=(session,),
        academic_group_capacities={
            session.academic_group_id: 60,
        },
        room_availability={
            room.id: ResourceAvailability(
                resource_id=room.id,
                windows=(
                    AvailabilityWindow(
                        day=Day.MONDAY,
                        start_period=1,
                        end_period=4,
                    ),
                ),
            ),
        },
    )

    placement = SessionPlacement(
        session=session,
        day=Day.MONDAY,
        start_period=2,
    )

    result = candidate_rooms_for_placement(
        placement,
        (room,),
        timetable_input,
    )

    assert result == ()