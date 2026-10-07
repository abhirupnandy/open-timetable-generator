from __future__ import annotations

import csv
from pathlib import Path

from app.domain.timetable_views import TimetableViewEntry


def export_timetable_csv(
    entries: tuple[TimetableViewEntry, ...],
    output_path: str | Path,
) -> Path:
    """Export timetable entries to a flat CSV file."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "Session ID",
        "Day",
        "Start Period",
        "End Period",
        "Duration",
        "Subject",
        "Course Code",
        "Course Name",
        "Academic Group Code",
        "Academic Group Name",
        "Faculty",
        "Room",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for entry in entries:
            writer.writerow(
                {
                    "Session ID": entry.session_id,
                    "Day": entry.day.value,
                    "Start Period": entry.start_period,
                    "End Period": entry.end_period,
                    "Duration": (
                        entry.end_period
                        - entry.start_period
                        + 1
                    ),
                    "Subject": entry.subject_name,
                    "Course Code": entry.course_code,
                    "Course Name": entry.course_name,
                    "Academic Group Code": entry.academic_group_code,
                    "Academic Group Name": entry.academic_group_name,
                    "Faculty": entry.faculty_name,
                    "Room": entry.room_name or "ONLINE",
                }
            )

    return output_path
