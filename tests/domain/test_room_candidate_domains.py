from app.domain.availability import AvailabilityWindow
from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import RoomType, SchedulingRoom
from app.domain.room_candidate_domains import (
    EmptyRoomCandidateDomainError,
    build_room_candidate_domain,
)
from app.domain.timetable import SchedulingSession, TimetableInput


def make_session() -> SchedulingSession:
    return SchedulingSession(
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


def make_placement() -> SessionPlacement:
    return SessionPlacement(
        session=make_session(),
        day=Day.MONDAY,
        start_period=2,
    )


def make_room(
    room_id: int = 101,
    capacity: int = 60,
) -> SchedulingRoom:
    return SchedulingRoom(
        id=room_id,
        room_type=RoomType.LECTURE_HALL,
        capacity=capacity,
    )


def make_input(
    *,
    room_availability: dict[int, ResourceAvailability] | None = None,
) -> TimetableInput:
    return TimetableInput(
        days=(Day.MONDAY,),
        periods_per_day=6,
        sessions=(make_session(),),
        academic_group_capacities={30: 50},
        room_availability=room_availability,
    )


def test_build_room_candidate_domain_returns_suitable_room():
    placement = make_placement()
    room = make_room()

    result = build_room_candidate_domain(
        placement,
        (room,),
        make_input(),
    )

    assert result == (room,)


def test_build_room_candidate_domain_excludes_unsuitable_room():
    placement = make_placement()
    room = make_room(capacity=40)

    try:
        build_room_candidate_domain(
            placement,
            (room,),
            make_input(),
        )
    except EmptyRoomCandidateDomainError as exc:
        assert exc.session_placement == placement
    else:
        raise AssertionError("Expected EmptyRoomCandidateDomainError")


def test_build_room_candidate_domain_excludes_unavailable_room():
    placement = make_placement()
    room = make_room()

    availability = {
        room.id: ResourceAvailability(
            resource_id=room.id,
            windows=(
                AvailabilityWindow(
                    day=Day.MONDAY,
                    start_period=4,
                    end_period=6,
                ),
            ),
        ),
    }

    try:
        build_room_candidate_domain(
            placement,
            (room,),
            make_input(room_availability=availability),
        )
    except EmptyRoomCandidateDomainError as exc:
        assert exc.session_placement == placement
    else:
        raise AssertionError("Expected EmptyRoomCandidateDomainError")


def test_build_room_candidate_domain_returns_multiple_suitable_rooms():
    placement = make_placement()
    first = make_room(room_id=101)
    second = make_room(room_id=102)

    result = build_room_candidate_domain(
        placement,
        (first, second),
        make_input(),
    )

    assert result == (first, second)