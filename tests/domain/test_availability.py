import pytest

from app.domain.availability import AvailabilityWindow
from app.domain.timetable import Day


def test_availability_window_contains_session():
    window = AvailabilityWindow(
        day=Day.MONDAY,
        start_period=2,
        end_period=5,
    )

    assert window.contains(
        day=Day.MONDAY,
        start_period=2,
        duration_periods=2,
    )

    assert window.contains(
        day=Day.MONDAY,
        start_period=4,
        duration_periods=2,
    )


def test_availability_window_rejects_session_outside_window():
    window = AvailabilityWindow(
        day=Day.MONDAY,
        start_period=2,
        end_period=5,
    )

    assert not window.contains(
        day=Day.MONDAY,
        start_period=1,
        duration_periods=2,
    )

    assert not window.contains(
        day=Day.MONDAY,
        start_period=5,
        duration_periods=2,
    )


def test_availability_window_rejects_different_day():
    window = AvailabilityWindow(
        day=Day.MONDAY,
        start_period=2,
        end_period=5,
    )

    assert not window.contains(
        day=Day.TUESDAY,
        start_period=2,
        duration_periods=2,
    )


def test_availability_window_rejects_invalid_session_values():
    window = AvailabilityWindow(
        day=Day.MONDAY,
        start_period=2,
        end_period=5,
    )

    assert not window.contains(
        day=Day.MONDAY,
        start_period=0,
        duration_periods=2,
    )

    assert not window.contains(
        day=Day.MONDAY,
        start_period=2,
        duration_periods=0,
    )


def test_availability_window_rejects_invalid_start_period():
    with pytest.raises(ValueError, match="start_period"):
        AvailabilityWindow(
            day=Day.MONDAY,
            start_period=0,
            end_period=5,
        )


def test_availability_window_rejects_reversed_periods():
    with pytest.raises(ValueError, match="end_period"):
        AvailabilityWindow(
            day=Day.MONDAY,
            start_period=5,
            end_period=2,
        )