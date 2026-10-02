from app.domain.availability import AvailabilityWindow
from app.domain.calendar import Day
from app.domain.placement import SessionPlacement
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import RoomType, SchedulingRoom
from app.domain.scheduling_candidate import SchedulingCandidate
from app.domain.scheduling_candidates import build_scheduling_candidates
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
    room_id: int,
    capacity: int = 60,
    room_type: RoomType = RoomType.LECTURE_HALL,
) -> SchedulingRoom:
    return SchedulingRoom(
        id=room_id,
        room_type=room_type,
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


def test_build_scheduling_candidates_returns_one_candidate_per_suitable_room():
    placement = make_placement()
    first_room = make_room(101)
    second_room = make_room(102)

    result = build_scheduling_candidates(
        placement,
        (first_room, second_room),
        make_input(),
    )

    assert result == (
        SchedulingCandidate(
            placement=placement,
            room=first_room,
        ),
        SchedulingCandidate(
            placement=placement,
            room=second_room,
        ),
    )


def test_build_scheduling_candidates_excludes_unsuitable_room():
    placement = make_placement()
    suitable_room = make_room(101)
    unsuitable_room = make_room(
        102,
        room_type=RoomType.COMPUTER_LAB,
    )

    result = build_scheduling_candidates(
        placement,
        (suitable_room, unsuitable_room),
        make_input(),
    )

    assert result == (
        SchedulingCandidate(
            placement=placement,
            room=suitable_room,
        ),
    )


def test_build_scheduling_candidates_excludes_unavailable_room():
    placement = make_placement()
    available_room = make_room(101)
    unavailable_room = make_room(102)

    room_availability = {
        unavailable_room.id: ResourceAvailability(
            resource_id=unavailable_room.id,
            windows=(
                AvailabilityWindow(
                    day=Day.MONDAY,
                    start_period=4,
                    end_period=6,
                ),
            ),
        ),
    }

    result = build_scheduling_candidates(
        placement,
        (available_room, unavailable_room),
        make_input(room_availability=room_availability),
    )

    assert result == (
        SchedulingCandidate(
            placement=placement,
            room=available_room,
        ),
    )