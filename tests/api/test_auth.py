from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.db.models import TimetableRun

ADMIN = {"username": "admin", "password": "admin-pass-1", "full_name": "Admin"}


def _entry(session_id, faculty, code, group="G1", day="MONDAY", start=1):
    return {
        "session_id": session_id,
        "day": day,
        "start_period": start,
        "end_period": start,
        "subject": f"Subject {session_id}",
        "course_code": "C",
        "group_code": group,
        "group_name": group,
        "faculty": faculty,
        "faculty_code": code,
        "faculty_designation": "PROFESSOR",
        "room": "R1",
    }


RESULT = {
    "calendar": {
        "days": ["MONDAY", "TUESDAY"],
        "periods": [{"number": n, "start": None, "end": None} for n in (1, 2, 3)],
        "lunch_after_period": None,
        "blocked_slots": [],
    },
    "group_parents": {"G1": None},
    "entries": [
        _entry("a", "Dr One", "F1"),
        _entry("b", "Dr Two", "F2", start=2),
    ],
    "score_report": {"total_weighted_penalty": 0},
}


def _client(app) -> TestClient:
    return TestClient(app)


def _login(app, username, password) -> TestClient:
    client = _client(app)
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def admin(anon_client, unauthenticated_app) -> TestClient:
    assert anon_client.get("/api/v1/auth/status").json() == {"needs_setup": True}
    response = anon_client.post("/api/v1/auth/setup", json=ADMIN)
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "ADMIN"
    return anon_client


def _seed_faculty(admin):
    school = admin.post("/api/v1/schools", json={"code": "S", "name": "School"}).json()
    for code, name in (("F1", "Dr One"), ("F2", "Dr Two")):
        response = admin.post(
            "/api/v1/faculty",
            json={
                "employee_id": code,
                "name": name,
                "email": f"{code.lower()}@example.edu",
                "designation": "PROFESSOR",
                "school_id": school["id"],
            },
        )
        assert response.status_code == 201


def _add_run(app, status="succeeded"):
    with app.state.test_session_factory() as db:
        db.add(
            TimetableRun(
                id=f"run-{status}",
                status=status,
                stage="done",
                started_at=datetime.now(UTC),
                max_time_seconds=1,
                session_count=2,
                elapsed_seconds=1,
                log="secret log",
                error_summary="boom" if status == "failed" else None,
                result_json=json.dumps(RESULT),
                files_json='["timetable_master.csv"]',
            )
        )
        db.commit()


def test_everything_requires_sign_in(anon_client):
    for path in (
        "/api/v1/schools",
        "/api/v1/timetable/runs",
        "/api/v1/data/summary",
        "/api/v1/timetable/config",
        "/api/v1/users",
        "/api/v1/auth/me",
    ):
        assert anon_client.get(path).status_code == 401, path
    assert anon_client.get("/health").status_code == 200


def test_setup_only_once_and_login(admin, unauthenticated_app):
    assert admin.get("/api/v1/auth/me").json()["username"] == "admin"
    assert admin.post("/api/v1/auth/setup", json=ADMIN).status_code == 409
    assert admin.get("/api/v1/auth/status").json() == {"needs_setup": False}

    anon = _client(unauthenticated_app)
    bad = anon.post("/api/v1/auth/login", json={"username": "admin", "password": "nope"})
    assert bad.status_code == 401

    other = _login(unauthenticated_app, "ADMIN", ADMIN["password"])  # case-insensitive
    token = other.post(
        "/api/v1/auth/login", json={"username": "admin", "password": ADMIN["password"]}
    ).json()["token"]
    bearer = _client(unauthenticated_app)
    me = bearer.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200

    assert other.post("/api/v1/auth/logout").status_code == 204
    assert other.get("/api/v1/auth/me").status_code == 401


def test_password_change_signs_out_other_sessions(admin, unauthenticated_app):
    second = _login(unauthenticated_app, "admin", ADMIN["password"])
    wrong = admin.post(
        "/api/v1/auth/password", json={"current_password": "x", "new_password": "new-pass-22"}
    )
    assert wrong.status_code == 400
    response = admin.post(
        "/api/v1/auth/password",
        json={"current_password": ADMIN["password"], "new_password": "new-pass-22"},
    )
    assert response.status_code == 200
    assert admin.get("/api/v1/auth/me").status_code == 200  # re-issued cookie
    assert second.get("/api/v1/auth/me").status_code == 401


def test_coordinator_has_full_access_except_users(admin, unauthenticated_app):
    response = admin.post(
        "/api/v1/users",
        json={"username": "coord", "password": "coord-pass", "role": "COORDINATOR"},
    )
    assert response.status_code == 201
    coordinator = _login(unauthenticated_app, "coord", "coord-pass")

    assert coordinator.get("/api/v1/schools").status_code == 200
    assert coordinator.post("/api/v1/schools", json={"code": "X", "name": "X"}).status_code == 201
    assert coordinator.get("/api/v1/timetable/config").status_code == 200
    assert coordinator.get("/api/v1/users").status_code == 403


def test_admin_safeguards(admin):
    me = admin.get("/api/v1/auth/me").json()
    assert admin.patch(f"/api/v1/users/{me['id']}", json={"role": "COORDINATOR"}).status_code == 409
    assert admin.delete(f"/api/v1/users/{me['id']}").status_code == 409
    missing = admin.post(
        "/api/v1/users", json={"username": "f", "password": "password1", "role": "FACULTY"}
    )
    assert missing.status_code == 422
    unknown = admin.post(
        "/api/v1/users",
        json={
            "username": "f",
            "password": "password1",
            "role": "FACULTY",
            "faculty_employee_id": "NOPE",
        },
    )
    assert unknown.status_code == 404


def test_faculty_sees_only_their_own_timetable(admin, unauthenticated_app):
    _seed_faculty(admin)
    _add_run(unauthenticated_app)
    _add_run(unauthenticated_app, "failed")

    created = admin.post("/api/v1/users/faculty-accounts").json()["created"]
    assert [item["username"] for item in created] == ["F1", "F2"]
    assert admin.post("/api/v1/users/faculty-accounts").json()["created"] == []  # idempotent

    faculty = _login(unauthenticated_app, "F1", created[0]["password"])
    me = faculty.get("/api/v1/auth/me").json()
    assert me["role"] == "FACULTY"
    assert me["faculty"] == {
        "employee_id": "F1",
        "name": "Dr One",
        "designation": "PROFESSOR",
        "designation_label": "Prof.",
    }

    # No access to data, constraints, exports or other people's sessions.
    assert faculty.get("/api/v1/schools").status_code == 403
    assert faculty.get("/api/v1/timetable/config").status_code == 403
    assert faculty.post("/api/v1/timetable/runs", json={}).status_code == 403
    assert faculty.get("/api/v1/users").status_code == 403

    runs = faculty.get("/api/v1/timetable/runs").json()
    assert [run["id"] for run in runs] == ["run-succeeded"]
    assert faculty.get("/api/v1/timetable/runs/run-failed").status_code == 404

    detail = faculty.get("/api/v1/timetable/runs/run-succeeded").json()
    assert [entry["session_id"] for entry in detail["result"]["entries"]] == ["a"]
    assert detail["log"] == "" and detail["files"] == []
    assert "score_report" not in detail["result"]
    files = faculty.get("/api/v1/timetable/runs/run-succeeded/files/timetable_master.csv")
    assert files.status_code == 403

    pdf = faculty.get("/api/v1/timetable/runs/run-succeeded/pdf?by=faculty")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-type"] == "application/pdf"
    assert "inline" in pdf.headers["content-disposition"]
    own = faculty.get("/api/v1/timetable/runs/run-succeeded/pdf?by=faculty&entity=F1")
    assert own.status_code == 200
    other = "/api/v1/timetable/runs/run-succeeded/pdf"
    assert faculty.get(f"{other}?by=faculty&entity=F2").status_code == 403
    assert faculty.get(f"{other}?by=group").status_code == 403


def test_staff_pdf_for_one_or_all_entities(admin, unauthenticated_app):
    _add_run(unauthenticated_app)
    _add_run(unauthenticated_app, "failed")
    base = "/api/v1/timetable/runs/run-succeeded/pdf"

    every = admin.get(f"{base}?by=faculty&download=true")
    assert every.status_code == 200 and "attachment" in every.headers["content-disposition"]
    one = admin.get(f"{base}?by=faculty&entity=F2")
    assert one.status_code == 200 and len(one.content) < len(every.content)
    assert admin.get(f"{base}?by=group&entity=G1").status_code == 200
    assert admin.get(f"{base}?by=room").status_code == 200
    assert admin.get(f"{base}?by=nonsense").status_code == 422
    assert admin.get("/api/v1/timetable/runs/run-failed/pdf").status_code == 409
