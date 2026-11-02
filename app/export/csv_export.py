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


def load_previous_placements(
    path: str | Path,
    room_ids_by_name: dict[str, int],
):
    """Read a previously exported master CSV for ``stability_vs_previous``.

    Returns ``{session_id: PreviousPlacement}``. Online sessions (room
    "ONLINE") and unknown room names map to ``room_id=None``.
    """

    from app.domain.calendar import Day
    from app.domain.timetable import PreviousPlacement

    path = Path(path)
    placements: dict[str, PreviousPlacement] = {}

    with path.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            room_name = row.get("Room") or ""
            placements[row["Session ID"]] = PreviousPlacement(
                day=Day(row["Day"]),
                start_period=int(row["Start Period"]),
                room_id=room_ids_by_name.get(room_name),
            )

    return placements
