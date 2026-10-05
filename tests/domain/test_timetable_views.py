from app.domain.calendar import Day
from app.domain.timetable_views import (
    TimetableViewEntry,
    build_master_view,
)


def make_entry(
    *,
    session_id: str,
    day: Day,
    start_period: int,
    course_code: str,
    academic_group_code: str,
) -> TimetableViewEntry:
    return TimetableViewEntry(
        session_id=session_id,
        day=day,
        start_period=start_period,
        end_period=start_period,
        subject_name="Subject",
        course_code=course_code,
        course_name="Course",
        academic_group_name="Group",
        academic_group_code=academic_group_code,
        faculty_name="Faculty",
        room_name="C101",
    )


def test_build_master_view_sorts_by_day_and_period() -> None:
    entries = (
        make_entry(
            session_id="s3",
            day=Day.TUESDAY,
            start_period=1,
            course_code="BCA",
            academic_group_code="BCA-Y1",
        ),
        make_entry(
            session_id="s2",
            day=Day.MONDAY,
            start_period=3,
            course_code="BTECH-CSE",
            academic_group_code="BTECH-Y1-A",
        ),
        make_entry(
            session_id="s1",
            day=Day.MONDAY,
            start_period=1,
            course_code="BTECH-CSE",
            academic_group_code="BTECH-Y1-A",
        ),
    )

    result = build_master_view(entries)

    assert [entry.session_id for entry in result] == [
        "s1",
        "s2",
        "s3",
    ]


def test_build_master_view_uses_course_and_group_as_tiebreakers() -> None:
    entries = (
        make_entry(
            session_id="s3",
            day=Day.MONDAY,
            start_period=1,
            course_code="BCA",
            academic_group_code="BCA-Y1",
        ),
        make_entry(
            session_id="s2",
            day=Day.MONDAY,
            start_period=1,
            course_code="BTECH-CSE",
            academic_group_code="BTECH-Y2-A",
        ),
        make_entry(
            session_id="s1",
            day=Day.MONDAY,
            start_period=1,
            course_code="BTECH-CSE",
            academic_group_code="BTECH-Y1-A",
        ),
    )

    result = build_master_view(entries)

    assert [entry.session_id for entry in result] == [
        "s3",
        "s1",
        "s2",
    ]