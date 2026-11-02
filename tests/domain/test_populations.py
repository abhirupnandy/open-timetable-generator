from app.domain.conflicts import academic_group_conflict
from app.domain.placement import SessionPlacement
from app.domain.populations import GroupHierarchy
from app.domain.timetable import Day, SchedulingSession

PARENTS = {1: None, 2: 1, 3: 1, 4: 2, 5: None}


def test_leaves_and_overlap():
    hierarchy = GroupHierarchy(PARENTS)
    assert hierarchy.all_leaves() == (3, 4, 5)
    assert hierarchy.leaves_of(1) == (3, 4)
    assert hierarchy.leaves_of(2) == (4,)
    assert hierarchy.populations_overlap(1, 4)
    assert hierarchy.populations_overlap(4, 2)
    assert not hierarchy.populations_overlap(2, 3)  # siblings
    assert not hierarchy.populations_overlap(1, 5)


def _placement(group):
    session = SchedulingSession(
        id=f"s{group}",
        teaching_assignment_id=group,
        subject_id=1,
        course_id=1,
        academic_group_id=group,
        faculty_id=group,
        duration_periods=1,
        mode="IN_PERSON",
        required_room_type=None,
        session_number=1,
    )
    return SessionPlacement(session=session, day=Day.MONDAY, start_period=1)


def test_sibling_batches_do_not_conflict_but_parent_does():
    assert not academic_group_conflict(_placement(2), _placement(3), PARENTS)
    assert academic_group_conflict(_placement(1), _placement(4), PARENTS)
