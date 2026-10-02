import pytest

from app.domain.candidate_domains import (
    EmptyCandidateDomainError,
    build_candidate_domains,
)
from app.domain.problem import SchedulingProblem
from app.domain.timetable import (
    Day,
    SchedulingSession,
    TimetableInput,
)


def make_problem() -> SchedulingProblem:
    sessions = (
        SchedulingSession(
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
        ),
        SchedulingSession(
            id="assignment:1:session:2",
            teaching_assignment_id=1,
            subject_id=1,
            course_id=1,
            academic_group_id=1,
            faculty_id=1,
            duration_periods=1,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
            session_number=2,
        ),
    )

    timetable_input = TimetableInput(
        days=(Day.MONDAY, Day.TUESDAY),
        periods_per_day=4,
        sessions=sessions,
    )

    return SchedulingProblem(
        timetable_input=timetable_input,
    )


def test_build_candidate_domains_for_all_sessions():
    problem = make_problem()

    domains = build_candidate_domains(problem)

    assert set(domains) == {
        "assignment:1:session:1",
        "assignment:1:session:2",
    }

    assert len(domains["assignment:1:session:1"]) == 6
    assert len(domains["assignment:1:session:2"]) == 8


def test_candidate_domains_preserve_session_identity():
    problem = make_problem()

    domains = build_candidate_domains(problem)

    for session_id, placements in domains.items():
        assert placements
        assert all(
            placement.session.id == session_id
            for placement in placements
        )

def test_rejects_session_with_no_candidate_placements():
    session = SchedulingSession(
        id="assignment:99:session:1",
        teaching_assignment_id=99,
        subject_id=1,
        course_id=1,
        academic_group_id=1,
        faculty_id=1,
        duration_periods=5,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
        session_number=1,
    )

    problem = SchedulingProblem(
        timetable_input=TimetableInput(
            days=(Day.MONDAY,),
            periods_per_day=4,
            sessions=(session,),
        ),
    )

    with pytest.raises(EmptyCandidateDomainError) as exc_info:
        build_candidate_domains(problem)

    assert exc_info.value.session_id == "assignment:99:session:1"