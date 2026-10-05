from __future__ import annotations

import re

_YEAR_PATTERN = re.compile(r"(?:^|-)Y(?P<year>\d+)(?:-|$)")


def extract_academic_year(group_code: str) -> int:
    """Extract the academic year encoded in an academic-group code."""
    match = _YEAR_PATTERN.search(group_code)

    if match is None:
        raise ValueError(
            f"Academic-group code does not contain a year: {group_code!r}"
        )

    return int(match.group("year"))