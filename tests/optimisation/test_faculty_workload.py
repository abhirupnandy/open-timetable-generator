from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.optimisation.faculty_workload import calculate_s2_penalty


def _faculty(
    faculty_id: int,
    designation: str,
    teaching_hours: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        faculty_id=faculty_id,
        designation=designation,
        teaching_hours=teaching_hours,
    )


def test_equal_utilisation_has_zero_penalty() -> None:
    faculty = (
        _faculty(1, "ASSISTANT_PROFESSOR", 10),
        _faculty(2, "ASSISTANT_PROFESSOR", 10),
    )

    assert calculate_s2_penalty(faculty) == 0


def test_unequal_utilisation_has_positive_penalty() -> None:
    faculty = (
        _faculty(1, "ASSISTANT_PROFESSOR", 13),
        _faculty(2, "ASSISTANT_PROFESSOR", 10),
    )

    assert calculate_s2_penalty(faculty) > 0


def test_different_designations_are_balanced_independently() -> None:
    faculty = (
        _faculty(1, "ASSISTANT_PROFESSOR", 13),
        _faculty(2, "ASSISTANT_PROFESSOR", 10),
        _faculty(3, "ASSOCIATE_PROFESSOR", 11),
        _faculty(4, "ASSOCIATE_PROFESSOR", 8),
    )

    penalty = calculate_s2_penalty(faculty)

    assert penalty > 0


def test_different_capacities_are_normalised() -> None:
    faculty = (
        _faculty(1, "ASSISTANT_PROFESSOR", 13),
        _faculty(2, "ASSOCIATE_PROFESSOR", 11),
    )

    # Different designations are evaluated independently, so
    # equal utilisation across designations must not create a penalty.
    assert calculate_s2_penalty(faculty) == 0


def test_zero_assigned_hours_are_handled() -> None:
    faculty = (
        _faculty(1, "ASSISTANT_PROFESSOR", 0),
        _faculty(2, "ASSISTANT_PROFESSOR", 0),
    )

    assert calculate_s2_penalty(faculty) == 0


def test_single_faculty_in_designation_has_zero_penalty() -> None:
    faculty = (
        _faculty(1, "ASSISTANT_PROFESSOR", 10),
    )

    assert calculate_s2_penalty(faculty) == 0


def test_empty_faculty_collection_has_zero_penalty() -> None:
    assert calculate_s2_penalty(()) == 0


def test_negative_teaching_hours_are_rejected() -> None:
    faculty = (
        _faculty(1, "ASSISTANT_PROFESSOR", -1),
        _faculty(2, "ASSISTANT_PROFESSOR", 10),
    )

    with pytest.raises(ValueError):
        calculate_s2_penalty(faculty)