from app.domain.availability import AvailabilityWindow
from app.domain.candidates import candidate_placements
from app.domain.resource_availability import ResourceAvailability
from app.domain.timetable import (
    Day,
    SchedulingSession,
    TimetableInput,
)


def make_input() -> TimetableInput:
    session = SchedulingSession(
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

    return TimetableInput(
        days=(Day.MONDAY, Day.TUESDAY),
        periods_per_day=4,
        sessions=(session,),
    )


def test_generates_all_candidate_placements():
    timetable_input = make_input()

    candidates = candidate_placements(
        "assignment:1:session:1",
        timetable_input,
    )

    assert len(candidates) == 6

    assert candidates[0].day == Day.MONDAY
    assert candidates[0].start_period == 1

    assert candidates[-1].day == Day.TUESDAY
    assert candidates[-1].start_period == 3


def test_candidate_placements_are_within_grid():
    timetable_input = make_input()

    candidates = candidate_placements(
        "assignment:1:session:1",
        timetable_input,
    )

    assert all(
        candidate.end_period <= timetable_input.periods_per_day
        for candidate in candidates
    )


def test_candidate_placements_preserve_session():
    timetable_input = make_input()

    candidates = candidate_placements(
        "assignment:1:session:1",
        timetable_input,
    )

    assert all(
        candidate.session.id == "assignment:1:session:1"
        for candidate in candidates
    )


def test_candidate_placements_are_contiguous():
    session = SchedulingSession(
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

    timetable_input = TimetableInput(
        days=(Day.MONDAY,),
        periods_per_day=4,
        sessions=(session,),
    )

    placements = candidate_placements(
        session.id,
        timetable_input,
    )

    assert len(placements) == 3

    for placement in placements:
        assert placement.occupied_periods == tuple(
            range(
                placement.start_period,
                placement.end_period + 1,
            )
        )


def test_candidate_placements_respect_availability():
    session = SchedulingSession(
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

    timetable_input = TimetableInput(
        days=(Day.MONDAY,),
        periods_per_day=6,
        sessions=(session,),
        faculty_availability={
            session.faculty_id: ResourceAvailability(
                resource_id=session.faculty_id,
                windows=(
                    AvailabilityWindow(
                        day=Day.MONDAY,
                        start_period=2,
                        end_period=5,
                    ),
                ),
            )
        },
    )

    placements = candidate_placements(
        session.id,
        timetable_input,
    )

    assert tuple(
        placement.start_period
        for placement in placements
    ) == (2, 3, 4)


def test_candidate_placements_exclude_unavailable_day():
    session = SchedulingSession(
        id="assignment:1:session:1",
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

    timetable_input = TimetableInput(
        days=(Day.MONDAY, Day.TUESDAY),
        periods_per_day=4,
        sessions=(session,),
        faculty_availability={
            session.faculty_id: ResourceAvailability(
                resource_id=session.faculty_id,
                windows=(
                    AvailabilityWindow(
                        day=Day.TUESDAY,
                        start_period=2,
                        end_period=4,
                    ),
                ),
            )
        },
    )

    placements = candidate_placements(
        session.id,
        timetable_input,
    )

    assert all(
        placement.day == Day.TUESDAY
        for placement in placements
    )
    assert tuple(
        placement.start_period
        for placement in placements
    ) == (2, 3, 4)


def test_candidate_placements_respect_resource_availability():
    session = SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=1,
        faculty_id=10,
        duration_periods=2,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )

    timetable_input = TimetableInput(
        days=(Day.MONDAY,),
        periods_per_day=6,
        sessions=(session,),
        faculty_availability={
            session.faculty_id: ResourceAvailability(
                resource_id=session.faculty_id,
                windows=(
                    AvailabilityWindow(
                        day=Day.MONDAY,
                        start_period=2,
                        end_period=5,
                    ),
                ),
            )
        },
    )

    placements = candidate_placements(
        session.id,
        timetable_input,
    )

    assert tuple(
        placement.start_period
        for placement in placements
    ) == (2, 3, 4)


def test_candidate_placements_use_faculty_availability_from_input():
    session = SchedulingSession(
        id="assignment:1:session:1",
        teaching_assignment_id=1,
        subject_id=1,
        course_id=1,
        academic_group_id=1,
        faculty_id=10,
        duration_periods=2,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )

    timetable_input = TimetableInput(
        days=(Day.MONDAY,),
        periods_per_day=6,
        sessions=(session,),
        faculty_availability={
            10: ResourceAvailability(
                resource_id=10,
                windows=(
                    AvailabilityWindow(
                        day=Day.MONDAY,
                        start_period=2,
                        end_period=5,
                    ),
                ),
            ),
        },
    )

    placements = candidate_placements(
        session.id,
        timetable_input,
    )

    assert tuple(
        placement.start_period
        for placement in placements
    ) == (2, 3, 4)