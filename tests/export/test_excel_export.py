from openpyxl import load_workbook

from app.domain.calendar import Day
from app.domain.timetable_views import TimetableViewEntry
from app.export.excel_export import (
    export_all,
    export_day_workbook,
    export_faculty_workbook,
    export_grid_workbook,
    export_master_workbook,
)
from app.export.layout import ExportCalendar, day_cells, faculty_loads
from app.export.pdf_export import timetable_pdf

CALENDAR = ExportCalendar(
    days=("MONDAY", "TUESDAY"),
    periods_per_day=4,
    period_times={
        1: ("08:00", "09:00"),
        2: ("09:00", "10:00"),
        3: ("10:00", "11:00"),
        4: ("11:00", "12:00"),
    },
    lunch_after_period=2,
    blocked={("TUESDAY", 4): "Sports"},
)


def entry(
    session_id,
    group,
    faculty="Dr A",
    start=1,
    end=1,
    day=Day.MONDAY,
    room="R1",
    code=None,
    designation="ASSISTANT_PROFESSOR",
):
    return TimetableViewEntry(
        session_id=session_id,
        day=day,
        start_period=start,
        end_period=end,
        subject_name=f"Subject {session_id}",
        course_code="C1",
        course_name="Course",
        academic_group_name=f"{group} name",
        academic_group_code=group,
        faculty_name=faculty,
        room_name=room,
        faculty_code=code or faculty.replace(" ", "").upper(),
        faculty_designation=designation,
    )


def values(worksheet):
    return [[cell for cell in row] for row in worksheet.iter_rows(values_only=True)]


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


def test_master_workbook_is_readable_without_session_ids(tmp_path):
    entries = (
        entry("a", "G1", start=1, end=2),
        entry("b", "G2", faculty="Ravi Kumar", designation="PHD_SCHOLAR", day=Day.TUESDAY),
    )
    path = export_master_workbook(
        entries, tmp_path / "master.xlsx", summary_rows=[["Status", "OPTIMAL"]], calendar=CALENDAR
    )
    workbook = load_workbook(path)
    assert workbook.sheetnames == ["Summary", "Timetable", "Faculty load"]
    assert workbook["Summary"]["B1"].value == "OPTIMAL"

    rows = values(workbook["Timetable"])
    header = rows[3]
    assert header == [
        "Day",
        "Time",
        "Periods",
        "Subject",
        "Course",
        "Group",
        "Faculty",
        "Designation",
        "Room",
    ]
    assert rows[4] == [
        "Monday",
        "08:00–10:00",
        "P1–P2",
        "Subject a",
        "C1",
        "G1",
        "Dr A",
        "Asst. Prof.",
        "R1",
    ]
    assert rows[5][6:8] == ["Ravi Kumar", "PhD Scholar"]
    assert not any("a" == cell for row in rows for cell in row)  # no session IDs


def test_faculty_load_counts_periods_per_day_and_week(tmp_path):
    entries = (
        entry("a", "G1", start=1, end=2),
        entry("b", "G2", start=3, end=3, day=Day.TUESDAY),
        entry("c", "G3", faculty="Dr B", start=1),
    )
    loads = {load.name: load for load in faculty_loads(entries)}
    assert loads["Dr A"].per_day == {"MONDAY": 2, "TUESDAY": 1}
    assert loads["Dr A"].weekly == 3 and loads["Dr A"].sessions == 2
    assert loads["Dr B"].weekly == 1

    path = export_master_workbook(entries, tmp_path / "master.xlsx", calendar=CALENDAR)
    rows = values(load_workbook(path)["Faculty load"])
    assert rows[3] == [
        "Employee ID",
        "Faculty",
        "Designation",
        "Mon",
        "Tue",
        "Weekly load",
        "Busiest day",
        "Sessions",
    ]
    assert rows[4] == ["DRA", "Dr A", "Asst. Prof.", 2, 1, 3, 2, 2]
    assert rows[6][1] == "Total" and rows[6][5] == "=SUM(F5:F6)"


def test_faculty_grid_has_daily_and_weekly_load(tmp_path):
    entries = (entry("a", "G1", start=1, end=2), entry("b", "G2", start=3, end=3, day=Day.TUESDAY))
    path = export_grid_workbook(entries, tmp_path / "grid.xlsx", by="faculty", calendar=CALENDAR)
    sheet = load_workbook(path).worksheets[0]
    assert sheet.title == "Dr A (Asst. Prof.)"
    assert sheet["A1"].value == "Faculty: Dr A (Asst. Prof.)"

    rows = values(sheet)
    assert rows[3] == [
        "Day",
        "P1\n08:00–09:00",
        "P2\n09:00–10:00",
        "Lunch",
        "P3\n10:00–11:00",
        "P4\n11:00–12:00",
        "Load\n(periods)",
    ]
    assert rows[4][0] == "Monday" and rows[4][-1] == 2
    assert rows[5][0] == "Tuesday" and rows[5][-1] == 1
    assert rows[5][5] == "Sports"  # blocked slot
    assert rows[6][-2:] == ["Weekly load", 3]
    assert "B5:C5" in {str(merged) for merged in sheet.merged_cells.ranges}  # two-period session


def test_group_grid_includes_parent_sessions(tmp_path):
    entries = (
        entry("lecture", "G1", start=1),
        entry("lab", "G1-B1", faculty="Dr B", start=3, end=4, room="LAB"),
        entry("other", "G2", faculty="Dr C", start=4),
    )
    path = export_grid_workbook(
        entries,
        tmp_path / "grid.xlsx",
        by="group",
        group_parents={"G1": None, "G1-B1": "G1", "G2": None},
        calendar=CALENDAR,
    )
    workbook = load_workbook(path)
    assert set(workbook.sheetnames) == {"G1", "G1-B1", "G2"}

    batch = workbook["G1-B1"]
    assert batch["A5"].value == "Monday"
    assert "Subject lecture" in str(batch["B5"].value)  # parent lecture shown to batch
    assert "Dr A (Asst. Prof.)" in str(batch["B5"].value)
    assert "Subject lab" in str(batch["E5"].value)
    assert "E5:F5" in {str(merged) for merged in batch.merged_cells.ranges}
    assert batch["A6"].value == "Tuesday"


def test_day_cells_do_not_merge_across_lunch():
    entries = (entry("long", "G1", start=1, end=4),)
    cells = day_cells(entries, "MONDAY", CALENDAR)
    assert [(cell.period, cell.span) for cell in cells] == [(1, 2), (3, 2)]


def test_export_all_and_pdf(tmp_path):
    entries = (
        entry("a", "G1", start=1, end=2),
        entry("b", "G2", faculty="Ravi Kumar", designation="PHD_SCHOLAR", day=Day.TUESDAY),
    )
    written = export_all(entries, tmp_path, calendar=CALENDAR, group_parents={})
    assert set(written) == {
        "timetable_master.xlsx",
        "timetable_by_day.xlsx",
        "timetable_by_faculty.xlsx",
        "grid_by_group.xlsx",
        "grid_by_faculty.xlsx",
        "grid_by_room.xlsx",
    }
    faculty = load_workbook(written["timetable_by_faculty.xlsx"])
    assert faculty.sheetnames == ["Faculty load", "Dr A (Asst. Prof.)", "Ravi Kumar (PhD Scholar)"]

    pdf = timetable_pdf(entries, CALENDAR, by="faculty")
    assert pdf.startswith(b"%PDF") and pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ") >= 1
    single = timetable_pdf(entries, CALENDAR, by="faculty", keys=["RAVIKUMAR"])
    assert single.startswith(b"%PDF") and len(single) < len(pdf)


def test_group_blocks_show_on_overlapping_groups_only(tmp_path):
    calendar = ExportCalendar(
        days=("MONDAY", "TUESDAY"),
        periods_per_day=4,
        group_blocked=(
            ("G1", "TUESDAY", 2, "Sports"),
            ("G1-B2", "MONDAY", 4, "Seminar"),
        ),
    )
    parents = {"G1": None, "G1-B1": "G1", "G1-B2": "G1", "G2": None}
    entries = (
        entry("lecture", "G1", start=1),
        entry("lab", "G1-B1", faculty="Dr B", start=3, end=3),
        entry("other", "G2", faculty="Dr C", start=1),
    )

    assert calendar.for_entity("group", "G1-B1", parents).blocked == {("TUESDAY", 2): "Sports (G1)"}
    assert calendar.for_entity("group", "G1", parents).blocked == {
        ("TUESDAY", 2): "Sports",
        ("MONDAY", 4): "Seminar (G1-B2)",
    }
    assert calendar.for_entity("group", "G2", parents).blocked == {}
    assert calendar.for_entity("faculty", "DRA", parents) is calendar

    path = export_grid_workbook(
        entries, tmp_path / "grid.xlsx", by="group", group_parents=parents, calendar=calendar
    )
    workbook = load_workbook(path)
    assert workbook["G1-B1"]["C6"].value == "Sports (G1)"  # Tuesday P2
    assert workbook["G1"]["E5"].value == "Seminar (G1-B2)"  # Monday P4
    g2 = [cell for row in workbook["G2"].iter_rows(values_only=True) for cell in row]
    assert "Sports" not in " ".join(str(cell) for cell in g2)

    faculty = export_grid_workbook(entries, tmp_path / "f.xlsx", by="faculty", calendar=calendar)
    cells = [
        c for ws in load_workbook(faculty) for row in ws.iter_rows(values_only=True) for c in row
    ]
    assert not any("Sports" in str(cell) for cell in cells)

    pdf = timetable_pdf(entries, calendar, by="group", keys=["G1-B1"], group_parents=parents)
    assert pdf.startswith(b"%PDF")
