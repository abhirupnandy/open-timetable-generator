from __future__ import annotations

from app.api.v1._common import get_timetable_config
from app.core.timetable_config import TimetableConfig


def _setup(client):
    school = client.post("/api/v1/schools", json={"code": "S1", "name": "School"}).json()
    course = client.post(
        "/api/v1/courses",
        json={
            "code": "C1",
            "name": "Course",
            "school_id": school["id"],
            "duration_years": 4,
            "total_semesters": 8,
        },
    ).json()
    faculty = client.post(
        "/api/v1/faculty",
        json={
            "employee_id": "F1",
            "name": "Scholar",
            "email": "phd@example.edu",
            "designation": "PHD_SCHOLAR",
            "school_id": school["id"],
            "preferred_day_off": "FRIDAY",
        },
    ).json()
    room = client.post(
        "/api/v1/rooms",
        json={
            "code": "R1",
            "name": "Room",
            "room_type": "CLASSROOM",
            "capacity": 60,
            "school_id": school["id"],
        },
    ).json()
    lecture = client.post(
        "/api/v1/subjects", json={"code": "L1", "name": "Lecture", "subject_type": "LECTURE"}
    ).json()
    lab = client.post(
        "/api/v1/subjects", json={"code": "B1", "name": "Lab", "subject_type": "LAB"}
    ).json()
    group = client.post(
        "/api/v1/groups",
        json={"code": "G1", "name": "G", "group_type": "GROUP", "course_id": course["id"]},
    ).json()
    return school, course, faculty, room, lecture, lab, group


def _assignment(course, faculty, subject, group, **extra):
    return {
        "subject_id": subject["id"],
        "course_id": course["id"],
        "academic_group_id": group["id"],
        "faculty_id": faculty["id"],
        "sessions_per_week": 2,
        "duration_periods": 1,
        "mode": "IN_PERSON",
        "required_room_type": "CLASSROOM",
        **extra,
    }


def test_faculty_preferred_day_off_round_trips(client):
    _, _, faculty, *_ = _setup(client)
    assert faculty["preferred_day_off"] == "FRIDAY"
    updated = client.patch(f"/api/v1/faculty/{faculty['id']}", json={"preferred_day_off": None})
    assert updated.json()["preferred_day_off"] is None


def test_unavailability_crud(client):
    _, _, faculty, room, *_ = _setup(client)
    payload = {
        "resource_type": "FACULTY",
        "resource_id": faculty["id"],
        "day": "MONDAY",
        "start_period": 1,
        "end_period": 3,
        "reason": "Committee",
    }
    created = client.post("/api/v1/unavailability", json=payload)
    assert created.status_code == 201
    item = created.json()

    assert client.get(f"/api/v1/unavailability/{item['id']}").json()["reason"] == "Committee"
    assert len(client.get("/api/v1/unavailability?resource_type=FACULTY").json()) == 1

    bad_range = client.patch(f"/api/v1/unavailability/{item['id']}", json={"end_period": 0})
    assert bad_range.status_code == 422
    assert (
        client.patch(f"/api/v1/unavailability/{item['id']}", json={"start_period": 5}).status_code
        == 422
    )

    room_payload = {**payload, "resource_type": "ROOM", "resource_id": room["id"]}
    assert client.post("/api/v1/unavailability", json=room_payload).status_code == 201
    missing = {**payload, "resource_id": 9999}
    assert client.post("/api/v1/unavailability", json=missing).status_code == 404
    inverted = {**payload, "start_period": 4, "end_period": 2}
    assert client.post("/api/v1/unavailability", json=inverted).status_code == 422

    assert client.delete(f"/api/v1/unavailability/{item['id']}").status_code == 204
    assert client.get(f"/api/v1/unavailability/{item['id']}").status_code == 404


def test_group_blocks_and_session_locks(client):
    _, course, faculty, room, lecture, _, group = _setup(client)
    block = client.post(
        "/api/v1/group-blocked-slots",
        json={"academic_group_id": group["id"], "day": "WEDNESDAY", "period": 7, "label": "Sports"},
    )
    assert block.status_code == 201
    duplicate = client.post(
        "/api/v1/group-blocked-slots",
        json={"academic_group_id": group["id"], "day": "WEDNESDAY", "period": 7},
    )
    assert duplicate.status_code == 409

    assignment = client.post(
        "/api/v1/assignments",
        json=_assignment(course, faculty, lecture, group, allow_across_lunch=True),
    ).json()
    assert assignment["allow_across_lunch"] is True

    lock = {
        "teaching_assignment_id": assignment["id"],
        "session_number": 1,
        "day": "TUESDAY",
        "start_period": 2,
        "room_id": room["id"],
    }
    assert client.post("/api/v1/session-locks", json=lock).status_code == 201
    assert client.post("/api/v1/session-locks", json=lock).status_code == 409
    too_many = {**lock, "session_number": 3}
    assert client.post("/api/v1/session-locks", json=too_many).status_code == 422
    assert client.post("/api/v1/session-locks", json={**lock, "room_id": 999}).status_code == 404


def test_role_restrictions_reject_assignment_when_enabled(test_app, client):
    _, course, faculty, _, lecture, lab, group = _setup(client)

    # Disabled by default: allowed.
    allowed = client.post("/api/v1/assignments", json=_assignment(course, faculty, lecture, group))
    assert allowed.status_code == 201

    data = TimetableConfig().model_dump(mode="json")
    data["hard"]["role_restrictions"]["enabled"] = True
    test_app.dependency_overrides[get_timetable_config] = lambda: TimetableConfig.model_validate(
        data
    )

    rejected = client.post("/api/v1/assignments", json=_assignment(course, faculty, lecture, group))
    assert rejected.status_code == 422
    assert "PHD_SCHOLAR" in rejected.json()["detail"]

    ok = client.post("/api/v1/assignments", json=_assignment(course, faculty, lab, group))
    assert ok.status_code == 201

    patched = client.patch(
        f"/api/v1/assignments/{ok.json()['id']}", json={"subject_id": lecture["id"]}
    )
    assert patched.status_code == 422
