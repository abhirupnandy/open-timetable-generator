from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from app.data_io.spec import SHEETS
from app.data_io.workbook import build_workbook, workbook_bytes

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_data.xlsx"


def _upload(client, data: bytes):
    return client.post(
        "/api/v1/data/import",
        content=data,
        headers={"Content-Type": "application/octet-stream"},
    )


def _workbook(rows: dict) -> bytes:
    return workbook_bytes(build_workbook(rows))


MINIMAL = {
    "Schools": [{"code": "S", "name": "School"}],
    "Courses": [
        {
            "code": "C",
            "name": "Course",
            "school_code": "S",
            "duration_years": 3,
            "total_semesters": 6,
        }
    ],
    "Faculty": [
        {
            "employee_id": "F1",
            "name": "Dr One",
            "email": "one@example.edu",
            "designation": "PROFESSOR",
            "school_code": "S",
        }
    ],
    "Rooms": [
        {"code": "R1", "name": "Room", "room_type": "CLASSROOM", "capacity": 50, "school_code": "S"}
    ],
    "Subjects": [{"code": "M", "name": "Maths", "subject_type": "LECTURE"}],
    "Groups": [
        {"code": "G", "name": "Group", "group_type": "GROUP", "course_code": "C", "capacity": 40},
        {
            "code": "G-B1",
            "name": "Batch",
            "group_type": "BATCH",
            "course_code": "C",
            "parent_group_code": "G",
        },
    ],
    "Assignments": [
        {
            "subject_code": "M",
            "group_code": "G",
            "faculty_employee_id": "F1",
            "sessions_per_week": 2,
            "duration_periods": 1,
            "mode": "IN_PERSON",
            "required_room_type": "CLASSROOM",
        }
    ],
    "SessionLocks": [
        {
            "subject_code": "M",
            "group_code": "G",
            "session_number": 1,
            "day": "MONDAY",
            "start_period": 2,
        }
    ],
}


def test_template_has_instructions_headers_and_dropdowns(client):
    response = client.get("/api/v1/data/template?blank=true")
    assert response.status_code == 200
    assert "timetable_data_template.xlsx" in response.headers["content-disposition"]

    workbook = load_workbook(BytesIO(response.content))
    assert workbook.sheetnames == ["Instructions", *(sheet.name for sheet in SHEETS)]
    faculty = workbook["Faculty"]
    assert [cell.value for cell in faculty[1]][:4] == [
        "employee_id",
        "name",
        "email",
        "designation",
    ]
    assert faculty.max_row == 1  # blank template
    assert any(
        "PROFESSOR" in str(rule.formula1) for rule in faculty.data_validations.dataValidation
    )


def test_template_example_rows_import_and_solve(client, run_manager):
    response = client.get("/api/v1/data/template")
    workbook = load_workbook(BytesIO(response.content))
    faculty = workbook["Faculty"]
    assert faculty.max_row == 5 and faculty["D5"].value == "PHD_SCHOLAR"
    assert faculty["A2"].fill.fgColor.rgb.endswith("FFF2CC")  # highlighted as example
    assert "EXAMPLES" in str(workbook["Instructions"]["A3"].value)
    instructions = [row for row in workbook["Instructions"].iter_rows(values_only=True)]
    assert ("designation", "yes", "one of the listed values") == instructions[
        next(i for i, row in enumerate(instructions) if row[0] == "designation")
    ][:3]
    for sheet in SHEETS:
        assert workbook[sheet.name].max_row >= 2, f"{sheet.name} has no example"

    result = _upload(client, response.content).json()
    assert result["ok"], result["issues"]
    assert result["counts"]["Assignments"] == 6

    started = client.post("/api/v1/timetable/runs", json={"max_time_seconds": 5}).json()
    run_manager.wait(started["id"])
    detail = client.get(f"/api/v1/timetable/runs/{started['id']}").json()
    assert detail["status"] == "succeeded", detail["error_detail"]


def test_sample_imports_and_export_round_trips(client):
    assert client.get("/api/v1/data/sample").status_code == 200

    result = _upload(client, SAMPLE.read_bytes()).json()
    assert result["ok"], result["issues"]
    assert result["counts"]["Assignments"] == 80

    summary = client.get("/api/v1/data/summary").json()
    assert summary["teaching_assignments"] == 80 and summary["academic_groups"] == 48
    assert len(client.get("/api/v1/assignments").json()) == 80

    exported = client.get("/api/v1/data/export")
    again = _upload(client, exported.content).json()
    assert again["ok"] and again["counts"] == result["counts"]


def test_import_replaces_data_and_resolves_codes(client):
    assert _upload(client, SAMPLE.read_bytes()).json()["ok"]
    result = _upload(client, _workbook(MINIMAL)).json()
    assert result["ok"], result["issues"]

    groups = {group["code"]: group for group in client.get("/api/v1/groups").json()}
    assert set(groups) == {"G", "G-B1"}
    assert groups["G-B1"]["parent_group_id"] == groups["G"]["id"]
    locks = client.get("/api/v1/session-locks").json()
    assert locks[0]["day"] == "MONDAY" and locks[0]["start_period"] == 2


def test_invalid_workbook_reports_every_issue_and_changes_nothing(client):
    _upload(client, _workbook(MINIMAL))

    broken = {key: [dict(row) for row in rows] for key, rows in MINIMAL.items()}
    broken["Faculty"][0]["designation"] = "LECTURER"
    broken["Rooms"][0]["capacity"] = "lots"
    broken["Groups"].append({"code": "G", "name": "Dup", "group_type": "GROUP", "course_code": "C"})
    broken["Assignments"][0]["group_code"] = "NOPE"
    broken["Assignments"].append(
        {
            "subject_code": "M",
            "group_code": "G",
            "faculty_employee_id": "F1",
            "sessions_per_week": 1,
            "duration_periods": 1,
            "mode": "IN_PERSON",
        }
    )

    result = _upload(client, _workbook(broken)).json()
    assert not result["ok"]
    issues = {
        (issue["sheet"], issue["row"], issue["column"]): issue["message"]
        for issue in result["issues"]
    }
    assert "must be one of" in issues[("Faculty", 2, "designation")]
    assert "whole number" in issues[("Rooms", 2, "capacity")]

    second = _upload(
        client,
        _workbook({**MINIMAL, "Groups": broken["Groups"], "Assignments": broken["Assignments"]}),
    ).json()
    messages = {(issue["sheet"], issue["column"]): issue["message"] for issue in second["issues"]}
    assert "duplicate code" in messages[("Groups", "code")]
    assert "not a code on the Groups sheet" in messages[("Assignments", "group_code")]
    assert "required when mode is IN_PERSON" in messages[("Assignments", "required_room_type")]

    assert [group["code"] for group in client.get("/api/v1/groups").json()] == ["G", "G-B1"]


def test_non_excel_upload_is_rejected(client):
    result = _upload(client, b"not a workbook").json()
    assert not result["ok"]
    assert "Not a valid .xlsx" in result["issues"][0]["message"]
    assert client.post("/api/v1/data/import", content=b"").status_code == 400


def test_clear_data(client):
    _upload(client, _workbook(MINIMAL))
    counts = client.post("/api/v1/data/clear").json()
    assert counts["teaching_assignments"] == 1
    assert client.get("/api/v1/data/summary").json()["schools"] == 0
