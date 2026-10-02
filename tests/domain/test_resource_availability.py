from app.domain.availability import AvailabilityWindow
from app.domain.resource_availability import ResourceAvailability
from app.domain.timetable import Day


def test_resource_availability_accepts_session_inside_window():
    availability = ResourceAvailability(
        resource_id=1,
        windows=(
            AvailabilityWindow(
                day=Day.MONDAY,
                start_period=2,
                end_period=5,
            ),
        ),
    )

    assert availability.is_available(
        day=Day.MONDAY,
        start_period=2,
        duration_periods=2,
    )


def test_resource_availability_rejects_session_outside_window():
    availability = ResourceAvailability(
        resource_id=1,
        windows=(
            AvailabilityWindow(
                day=Day.MONDAY,
                start_period=2,
                end_period=5,
            ),
        ),
    )

    assert not availability.is_available(
        day=Day.MONDAY,
        start_period=5,
        duration_periods=2,
    )


def test_resource_availability_rejects_unavailable_day():
    availability = ResourceAvailability(
        resource_id=1,
        windows=(
            AvailabilityWindow(
                day=Day.MONDAY,
                start_period=2,
                end_period=5,
            ),
        ),
    )

    assert not availability.is_available(
        day=Day.TUESDAY,
        start_period=2,
        duration_periods=2,
    )


def test_resource_availability_can_have_multiple_windows():
    availability = ResourceAvailability(
        resource_id=1,
        windows=(
            AvailabilityWindow(
                day=Day.MONDAY,
                start_period=1,
                end_period=3,
            ),
            AvailabilityWindow(
                day=Day.WEDNESDAY,
                start_period=4,
                end_period=6,
            ),
        ),
    )

    assert availability.is_available(
        day=Day.MONDAY,
        start_period=2,
        duration_periods=2,
    )

    assert availability.is_available(
        day=Day.WEDNESDAY,
        start_period=5,
        duration_periods=2,
    )

    assert not availability.is_available(
        day=Day.TUESDAY,
        start_period=1,
        duration_periods=1,
    )