import pytest

from app.domain.academic_group_view import extract_academic_year


@pytest.mark.parametrize(
    ("group_code", "expected_year"),
    [
        ("BTECH-Y1-A1", 1),
        ("BTECH-Y1-B2", 1),
        ("BTECH-Y2-A", 2),
        ("BCA-Y1", 1),
        ("BCA-Y2-A2", 2),
        ("MTECH-Y1-A1", 1),
    ],
)
def test_extract_academic_year(group_code: str, expected_year: int) -> None:
    assert extract_academic_year(group_code) == expected_year


def test_extract_academic_year_rejects_code_without_year() -> None:
    with pytest.raises(ValueError, match="does not contain a year"):
        extract_academic_year("BTECH-A1")