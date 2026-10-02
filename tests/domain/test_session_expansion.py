import pytest

from app.domain.session_expansion import expand_teaching_assignment


def test_expand_teaching_assignment():
    sessions = expand_teaching_assignment(
        teaching_assignment_id=12,
        subject_id=5,
        course_id=2,
        academic_group_id=7,
        faculty_id=3,
        sessions_per_week=3,
        duration_periods=2,
        mode="IN_PERSON",
        required_room_type="LECTURE_HALL",
    )

    assert len(sessions) == 3

    assert [session.session_number for session in sessions] == [1, 2, 3]

    assert [session.id for session in sessions] == [
        "assignment:12:session:1",
        "assignment:12:session:2",
        "assignment:12:session:3",
    ]

    assert all(session.teaching_assignment_id == 12 for session in sessions)
    assert all(session.duration_periods == 2 for session in sessions)
    assert all(session.mode == "IN_PERSON" for session in sessions)
    assert all(session.required_room_type == "LECTURE_HALL" for session in sessions)


@pytest.mark.parametrize(
    ("sessions_per_week", "duration_periods"),
    [
        (0, 2),
        (-1, 2),
        (3, 0),
        (3, -1),
    ],
)
def test_expand_teaching_assignment_rejects_invalid_values(
    sessions_per_week: int,
    duration_periods: int,
):
    with pytest.raises(ValueError):
        expand_teaching_assignment(
            teaching_assignment_id=12,
            subject_id=5,
            course_id=2,
            academic_group_id=7,
            faculty_id=3,
            sessions_per_week=sessions_per_week,
            duration_periods=duration_periods,
            mode="IN_PERSON",
            required_room_type="LECTURE_HALL",
        )