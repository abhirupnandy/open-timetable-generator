from app.domain.calendar import Day
from app.domain.db_input import unavailability_to_availability

MON, TUE = Day.MONDAY, Day.TUESDAY


def test_unavailability_becomes_availability_windows():
    result = unavailability_to_availability(
        [(7, MON, 3, 4), (7, MON, 8, 8)],
        days=(MON, TUE),
        periods_per_day=8,
    )

    windows = {(w.day, w.start_period, w.end_period) for w in result[7].windows}
    assert windows == {(MON, 1, 2), (MON, 5, 7), (TUE, 1, 8)}

    availability = result[7]
    assert availability.is_available(day=MON, start_period=1, duration_periods=2)
    assert not availability.is_available(day=MON, start_period=2, duration_periods=2)
    assert availability.is_available(day=TUE, start_period=3, duration_periods=2)


def test_resources_without_unavailability_are_absent():
    assert unavailability_to_availability([], days=(MON,), periods_per_day=8) == {}


def test_fully_unavailable_day_has_no_window():
    result = unavailability_to_availability([(1, MON, 1, 8)], days=(MON,), periods_per_day=8)
    assert result[1].windows == ()
