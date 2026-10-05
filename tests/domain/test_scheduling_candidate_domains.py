from app.domain.availability import AvailabilityWindow
from app.domain.calendar import Day
from app.domain.problem import SchedulingProblem
from app.domain.resource_availability import ResourceAvailability
from app.domain.room import RoomType, SchedulingRoom
from app.domain.scheduling_candidate import SchedulingCandidate
from app.domain.scheduling_candidate_domains import (
    build_scheduling_candidate_domains,
)
from app.domain.timetable import SchedulingSession, TimetableInput


def make_session(
    *,
    mode: str = "IN_PERSON",
) -> SchedulingSession:
    return SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=10,
        course_id=20,
        academic_group_id=30,
        faculty_id=40,
        duration_periods=2,
        mode=mode,
        required_room_type="LECTURE_HALL",
        session_number=1,
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
    session: SchedulingSession | None = None,
    room_availability: dict[int, ResourceAvailability] | None = None,
) -> TimetableInput:
    session = session or make_session()

    return TimetableInput(
        days=(Day.MONDAY,),
        periods_per_day=6,
        sessions=(session,),
        academic_group_capacities={30: 50},
        room_availability=room_availability,
        rooms=(make_room(),),
    )


def make_problem(
    *,
    session: SchedulingSession | None = None,
    room_availability: dict[int, ResourceAvailability] | None = None,
) -> SchedulingProblem:
    return SchedulingProblem(
        timetable_input=make_input(
            session=session,
            room_availability=room_availability,
        )
    )


def test_build_scheduling_candidate_domains_returns_physical_candidates():
    problem = make_problem()

    result = build_scheduling_candidate_domains(problem)

    assert len(result) == 1

    candidates = result["assignment:1:session:1"]

    assert len(candidates) == 5
    assert all(isinstance(candidate, SchedulingCandidate) for candidate in candidates)
    assert all(candidate.room is not None for candidate in candidates)


def test_build_scheduling_candidate_domains_returns_online_candidate_without_room():
    session = make_session(mode="ONLINE")
    problem = make_problem(session=session)

    result = build_scheduling_candidate_domains(problem)

    candidates = result["assignment:1:session:1"]

    assert len(candidates) == 5
    assert all(candidate.room is None for candidate in candidates)


def test_build_scheduling_candidate_domains_keeps_valid_placements_when_one_room_is_unavailable():
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

    problem = make_problem(room_availability=availability)

    result = build_scheduling_candidate_domains(problem)

    candidates = result["assignment:1:session:1"]

    assert len(candidates) == 2
    assert all(candidate.room == room for candidate in candidates)


def test_build_scheduling_candidate_domains_raises_when_no_room_is_available():
    room = make_room()

    availability = {
        room.id: ResourceAvailability(
            resource_id=room.id,
            windows=(
                AvailabilityWindow(
                    day=Day.MONDAY,
                    start_period=6,
                    end_period=6,
                ),
            ),
        ),
    }

    problem = make_problem(room_availability=availability)

    try:
        build_scheduling_candidate_domains(problem)
    except ValueError as exc:
        assert exc.args
    else:
        raise AssertionError("Expected ValueError")