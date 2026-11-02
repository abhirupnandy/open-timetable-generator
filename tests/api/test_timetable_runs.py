from __future__ import annotations

from app.db.models import TimetableRun


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


def test_config_can_be_edited_validated_and_reset(client, config_store):
    config = client.get("/api/v1/timetable/config").json()["config"]
    config["soft"]["faculty_gaps"]["weight"] = 5
    config["constraints"]["no_session_across_lunch"]["mode"] = "hard"
    config["calendar"]["lunch_after_period"] = None
    config["hard"]["role_restrictions"]["PHD_SCHOLAR"] = None

    saved = client.put("/api/v1/timetable/config", json=config)
    assert saved.status_code == 200
    assert saved.json()["config"]["soft"]["faculty_gaps"]["weight"] == 5

    reloaded = config_store.load()
    assert reloaded.soft.faculty_gaps.weight == 5
    assert reloaded.calendar.lunch_after_period is None
    assert reloaded.hard.role_restrictions.PHD_SCHOLAR is None
    assert 'mode = "hard"' in config_store.path.read_text()

    config["soft"]["faculty_gaps"]["weight"] = -1
    config["soft"]["typo_constraint"] = {"enabled": True}
    bad = client.put("/api/v1/timetable/config", json=config)
    assert bad.status_code == 422
    messages = " ".join(item["msg"] for item in bad.json()["detail"])
    assert "greater than or equal to 0" in messages and "Extra inputs" in messages
    assert config_store.load().soft.faculty_gaps.weight == 5  # unchanged

    reset = client.post("/api/v1/timetable/config/reset").json()
    assert reset["config"]["soft"]["faculty_gaps"]["weight"] == 75


def test_config_schema(client):
    schema = client.get("/api/v1/timetable/config/schema").json()
    assert "calendar" in schema["properties"] and "$defs" in schema


def _start(client, run_manager, seconds=2):
    response = client.post("/api/v1/timetable/runs", json={"max_time_seconds": seconds})
    assert response.status_code == 202
    run_id = response.json()["id"]
    run_manager.wait(run_id)
    return client.get(f"/api/v1/timetable/runs/{run_id}").json()


def test_run_without_data_is_recorded_as_failed_with_reason(client, run_manager):
    detail = _start(client, run_manager)
    assert detail["status"] == "failed"
    assert "no active teaching assignments" in detail["error"]
    assert "Import a data workbook" in detail["error_detail"]
    assert "FAILED" in detail["log"]

    failures = client.get("/api/v1/timetable/runs?status_filter=failed").json()
    assert [run["id"] for run in failures] == [detail["id"]]


def test_infeasible_run_explains_why(client, run_manager):
    _seed_minimal(client)
    assignment = client.get("/api/v1/assignments").json()[0]
    client.patch(f"/api/v1/assignments/{assignment['id']}", json={"sessions_per_week": 20})

    detail = _start(client, run_manager)
    assert detail["status"] == "failed"
    assert detail["stage"] == "solving"
    assert "Pre-solve checks found" in detail["error"]
    assert "weekly cap is 13" in detail["error_detail"]


def test_run_solves_and_exposes_results_and_files(client, run_manager):
    _seed_minimal(client)

    detail = _start(client, run_manager)
    assert detail["status"] == "succeeded", detail["error_detail"]
    assert detail["session_count"] == 3
    assert detail["stage"] == "done"
    for stage in ("Loading scheduling data", "Solver finished", "Writing CSV"):
        assert stage in detail["log"]

    result = detail["result"]
    assert result["validation"]["is_valid"]
    assert len(result["entries"]) == 3
    assert result["calendar"]["periods"][0] == {"number": 1, "start": "08:20", "end": "09:20"}
    assert result["score_report"]["mismatches"] == []
    assert {item["name"] for item in detail["files"]} >= {
        "timetable_master.csv",
        "grid_by_group.xlsx",
    }

    run_id = detail["id"]
    csv = client.get(f"/api/v1/timetable/runs/{run_id}/files/timetable_master.csv")
    assert csv.status_code == 200 and "Session ID" in csv.text
    assert client.get(f"/api/v1/timetable/runs/{run_id}/files/..%2Fsecret").status_code == 404

    assert client.delete(f"/api/v1/timetable/runs/{run_id}").status_code == 204
    assert client.get(f"/api/v1/timetable/runs/{run_id}").status_code == 404
    assert not (run_manager.files_dir(run_id) / "timetable_master.csv").exists()


def test_only_one_run_at_a_time(client, run_manager):
    from datetime import UTC, datetime

    with run_manager.session_factory() as db:
        db.add(
            TimetableRun(
                id="busy",
                status="running",
                stage="solving",
                started_at=datetime.now(UTC),
                max_time_seconds=1,
                session_count=1,
                elapsed_seconds=0,
                log="",
                files_json="[]",
            )
        )
        db.commit()

    assert client.post("/api/v1/timetable/runs", json={}).status_code == 409
    assert client.delete("/api/v1/timetable/runs/busy").status_code == 409


def test_interrupted_runs_are_marked_failed_on_startup(tmp_path, run_manager):
    from datetime import UTC, datetime

    from app.api.v1.timetable import RunManager

    with run_manager.session_factory() as db:
        db.add(
            TimetableRun(
                id="ghost",
                status="running",
                stage="solving",
                started_at=datetime.now(UTC),
                max_time_seconds=1,
                session_count=1,
                elapsed_seconds=0,
                log="",
                files_json="[]",
            )
        )
        db.commit()

    RunManager(run_manager.session_factory, tmp_path)

    with run_manager.session_factory() as db:
        ghost = db.get(TimetableRun, "ghost")
        assert ghost.status == "failed"
        assert "server stopped" in ghost.error_summary


def test_frontend_is_served_with_spa_fallback(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.frontend import mount_frontend

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text('<div id="root"></div>')
    (dist / "assets" / "index.js").write_text("console.log(1)")
    (dist / "favicon.svg").write_text("<svg/>")

    app = FastAPI()

    @app.get("/api/v1/ping")
    def ping():
        return {"ok": True}

    mount_frontend(app, dist)
    client = TestClient(app)

    assert client.get("/").text == '<div id="root"></div>'
    assert client.get("/timetable").text == '<div id="root"></div>'
    assert client.get("/data/rooms").text == '<div id="root"></div>'
    assert client.get("/assets/index.js").status_code == 200
    assert client.get("/favicon.svg").text == "<svg/>"
    assert client.get("/api/v1/ping").json() == {"ok": True}
    assert client.get("/api/v1/missing").status_code == 404
    assert client.get("/api/v1/missing").json() == {"detail": "Not Found"}
    assert client.get("/../pyproject.toml").text == '<div id="root"></div>'


def test_unbuilt_frontend_explains_how_to_build(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.frontend import mount_frontend

    app = FastAPI()
    mount_frontend(app, tmp_path / "missing")
    response = TestClient(app).get("/")
    assert response.status_code == 503
    assert "npm run build" in response.text
