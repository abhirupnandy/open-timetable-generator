import pytest

from app.domain.time_slots import valid_start_periods


@pytest.mark.parametrize(
    ("periods_per_day", "duration_periods", "expected"),
    [
        (8, 1, (1, 2, 3, 4, 5, 6, 7, 8)),
        (8, 2, (1, 2, 3, 4, 5, 6, 7)),
        (8, 3, (1, 2, 3, 4, 5, 6)),
        (8, 8, (1,)),
        (8, 9, ()),
        (6, 2, (1, 2, 3, 4, 5)),
    ],
)
def test_valid_start_periods(
    periods_per_day: int,
    duration_periods: int,
    expected: tuple[int, ...],
):
    assert valid_start_periods(
        periods_per_day=periods_per_day,
        duration_periods=duration_periods,
    ) == expected


@pytest.mark.parametrize(
    ("periods_per_day", "duration_periods"),
    [
        (0, 1),
        (-1, 1),
        (8, 0),
        (8, -1),
    ],
)
def test_valid_start_periods_rejects_invalid_values(
    periods_per_day: int,
    duration_periods: int,
):
    with pytest.raises(ValueError):
        valid_start_periods(
            periods_per_day=periods_per_day,
            duration_periods=duration_periods,
        )