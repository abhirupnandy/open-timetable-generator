from __future__ import annotations

import pytest

from app.api.v1.timetable import RunManager, TimetableRun, get_run_manager


@pytest.fixture
def manager(test_app, tmp_path):
    instance = RunManager(tmp_path)
    test_app.dependency_overrides[get_run_manager] = lambda: instance
    return instance


def _seed_minimal(client):
    school = client.post("/api/v1/schools", json={"code": "S", "name": "School"}).json()
    course = client.post(
        "/api/v1/courses",
        json={
            "code": "C",
            "name": "Course",
            "school_id": school["id"],
            "duration_years": 3,
            "total_semesters": 6,
        },
    ).json()
    faculty = client.post(
        "/api/v1/faculty",
        json={
            "employee_id": "F1",
            "name": "Dr One",
            "email": "one@example.edu",
            "designation": "ASSISTANT_PROFESSOR",
            "school_id": school["id"],
        },
    ).json()
    client.post(
        "/api/v1/rooms",
        json={
            "code": "R1",
            "name": "Room 1",
            "room_type": "CLASSROOM",
            "capacity": 60,
            "school_id": school["id"],
        },
    )
    subject = client.post(
        "/api/v1/subjects", json={"code": "MATH", "name": "Maths", "subject_type": "LECTURE"}
    ).json()
    group = client.post(
        "/api/v1/groups",
        json={
            "code": "G1",
            "name": "Group 1",
            "group_type": "GROUP",
            "course_id": course["id"],
            "capacity": 40,
        },
    ).json()
    response = client.post(
        "/api/v1/assignments",
        json={
            "subject_id": subject["id"],
            "course_id": course["id"],
            "academic_group_id": group["id"],
            "faculty_id": faculty["id"],
            "sessions_per_week": 3,
            "duration_periods": 1,
            "mode": "IN_PERSON",
            "required_room_type": "CLASSROOM",
        },
    )
    assert response.status_code == 201


def test_config_endpoint(client):
    body = client.get("/api/v1/timetable/config").json()
    assert body["config"]["calendar"]["lunch_after_period"] == 4
    assert any("student_gaps" in line for line in body["summary"])


def test_run_requires_assignments(client, manager):
    response = client.post("/api/v1/timetable/runs", json={"max_time_seconds": 1})
    assert response.status_code == 422


def test_run_solves_and_exposes_results_and_files(client, manager):
    _seed_minimal(client)

    started = client.post("/api/v1/timetable/runs", json={"max_time_seconds": 2})
    assert started.status_code == 202
    run_id = started.json()["id"]
    assert started.json()["session_count"] == 3

    run = manager.wait(run_id)
    assert run.status == "succeeded", run.error

    detail = client.get(f"/api/v1/timetable/runs/{run_id}").json()
    result = detail["result"]
    assert result["validation"]["is_valid"]
    assert len(result["entries"]) == 3
    assert {entry["group_code"] for entry in result["entries"]} == {"G1"}
    assert result["calendar"]["periods"][0] == {"number": 1, "start": "08:20", "end": "09:20"}
    assert result["score_report"]["mismatches"] == []
    assert {item["name"] for item in detail["files"]} >= {
        "timetable_master.csv",
        "grid_by_group.xlsx",
    }

    listing = client.get("/api/v1/timetable/runs").json()
    assert listing[0]["id"] == run_id and listing[0]["status"] == "succeeded"

    csv = client.get(f"/api/v1/timetable/runs/{run_id}/files/timetable_master.csv")
    assert csv.status_code == 200 and "Session ID" in csv.text
    assert client.get(f"/api/v1/timetable/runs/{run_id}/files/..%2Fsecret").status_code == 404
    assert client.get("/api/v1/timetable/runs/missing").status_code == 404


def test_only_one_run_at_a_time(client, manager):
    _seed_minimal(client)
    from datetime import UTC, datetime

    manager._runs["busy"] = TimetableRun(
        id="busy",
        status="running",
        started_at=datetime.now(UTC),
        max_time_seconds=1,
        session_count=1,
    )
    assert client.post("/api/v1/timetable/runs", json={}).status_code == 409


def test_frontend_is_served(client):
    index = client.get("/")
    assert index.status_code == 200
    assert "/static/app.js" in index.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/app.css").status_code == 200
