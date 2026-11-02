from openpyxl import load_workbook

from app.domain.calendar import Day
from app.domain.timetable_views import TimetableViewEntry
from app.export.excel_export import (
    export_day_workbook,
    export_faculty_workbook,
    export_grid_workbook,
    export_master_workbook,
)


def entry(session_id, group, faculty="Dr A", start=1, end=1, day=Day.MONDAY, room="R1"):
    return TimetableViewEntry(
        session_id=session_id,
        day=day,
        start_period=start,
        end_period=end,
        subject_name=f"Subject {session_id}",
        course_code="C1",
        course_name="Course",
        academic_group_name=group,
        academic_group_code=group,
        faculty_name=faculty,
        room_name=room,
    )


def test_exporters_handle_no_entries(tmp_path):
    for exporter in (export_master_workbook, export_day_workbook, export_faculty_workbook):
        path = exporter((), tmp_path / f"{exporter.__name__}.xlsx")
        assert load_workbook(path).sheetnames

    path = export_faculty_workbook((), tmp_path / "faculty.xlsx")
    assert load_workbook(path).sheetnames == ["No sessions"]

    grid = export_grid_workbook(
        (), tmp_path / "grid.xlsx", by="room", days=["MONDAY"], periods_per_day=4
    )
    assert load_workbook(grid).sheetnames == ["No sessions"]


def test_master_workbook_summary_sheet(tmp_path):
    path = export_master_workbook(
        (entry("a", "G1"),), tmp_path / "master.xlsx", summary_rows=[["Status", "OPTIMAL"]]
    )
    workbook = load_workbook(path)
    assert workbook.sheetnames == ["Summary", "Master"]
    assert workbook["Summary"]["B1"].value == "OPTIMAL"


def test_group_grid_includes_parent_sessions(tmp_path):
    entries = (
        entry("lecture", "G1", start=1),
        entry("lab", "G1-B1", faculty="Dr B", start=2, end=3, room="LAB"),
        entry("other", "G2", faculty="Dr C", start=4),
    )
    path = export_grid_workbook(
        entries,
        tmp_path / "grid.xlsx",
        by="group",
        days=["MONDAY", "TUESDAY"],
        periods_per_day=4,
        group_parents={"G1": None, "G1-B1": "G1", "G2": None},
    )
    workbook = load_workbook(path)
    assert set(workbook.sheetnames) == {"G1", "G1-B1", "G2"}

    batch = workbook["G1-B1"]
    assert [cell.value for cell in batch[1]] == ["Day", "P1", "P2", "P3", "P4"]
    assert "Subject lecture" in batch["B2"].value  # parent lecture shown to batch
    assert "Subject lab" in batch["C2"].value and "Subject lab" in batch["D2"].value
    assert batch["E2"].value in (None, "")
    assert batch["A3"].value == "Tuesday"
