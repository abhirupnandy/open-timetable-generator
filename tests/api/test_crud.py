def school_payload(code="SAI", name="School of AI"):
    return {"code": code, "name": name}


def create_school(client):
    response = client.post("/api/v1/schools", json=school_payload())
    assert response.status_code == 201
    return response.json()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_school_crud_and_conflicts(client):
    school = create_school(client)
    assert client.get("/api/v1/schools").status_code == 200
    assert client.get(f"/api/v1/schools/{school['id']}").status_code == 200
    updated = client.patch(
        f"/api/v1/schools/{school['id']}", json={"name": "School of Artificial Intelligence"}
    )
    assert updated.status_code == 200
    duplicate = client.post("/api/v1/schools", json=school_payload())
    assert duplicate.status_code == 409
    deleted = client.delete(f"/api/v1/schools/{school['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/schools/{school['id']}").status_code == 404


def test_all_entity_creation_and_filters(client):
    school = create_school(client)
    sid = school["id"]
    course = client.post(
        "/api/v1/courses",
        json={
            "code": "BTECH-AI",
            "name": "B.Tech AI",
            "school_id": sid,
            "duration_years": 4,
            "total_semesters": 8,
        },
    ).json()
    assert (
        client.post(
            "/api/v1/courses",
            json={
                "code": "BAD",
                "name": "Bad",
                "school_id": 999,
                "duration_years": 4,
                "total_semesters": 8,
            },
        ).status_code
        == 404
    )
    faculty = client.post(
        "/api/v1/faculty",
        json={
            "employee_id": "F001",
            "name": "A Teacher",
            "email": "a@example.edu",
            "designation": "ASSISTANT_PROFESSOR",
            "school_id": sid,
        },
    ).json()
    client.post(
        "/api/v1/rooms",
        json={
            "code": "LH-01",
            "name": "Lecture Hall 01",
            "room_type": "LECTURE_HALL",
            "capacity": 120,
            "school_id": sid,
        },
    )
    subject = client.post(
        "/api/v1/subjects",
        json={"code": "DS", "name": "Data Structures", "subject_type": "LECTURE"},
    ).json()
    group = client.post(
        "/api/v1/groups",
        json={
            "code": "G1",
            "name": "Group 1",
            "group_type": "GROUP",
            "course_id": course["id"],
            "capacity": 60,
        },
    ).json()
    batch = client.post(
        "/api/v1/groups",
        json={
            "code": "B1",
            "name": "Batch 1",
            "group_type": "BATCH",
            "course_id": course["id"],
            "parent_group_id": group["id"],
            "capacity": 30,
        },
    ).json()
    assert batch["parent_group_id"] == group["id"]
    assignment = client.post(
        "/api/v1/assignments",
        json={
            "subject_id": subject["id"],
            "course_id": course["id"],
            "academic_group_id": group["id"],
            "faculty_id": faculty["id"],
            "sessions_per_week": 3,
            "duration_periods": 1,
            "mode": "IN_PERSON",
            "required_room_type": "LECTURE_HALL",
        },
    )
    assert assignment.status_code == 201
    assert client.get(f"/api/v1/courses?school_id={sid}").status_code == 200
    assert client.get(f"/api/v1/faculty?school_id={sid}").status_code == 200
    assert client.get(f"/api/v1/rooms?school_id={sid}").status_code == 200
    assert client.get(f"/api/v1/groups?course_id={course['id']}").status_code == 200
    assert client.get(f"/api/v1/assignments?course_id={course['id']}").status_code == 200
    assert client.get(f"/api/v1/assignments?faculty_id={faculty['id']}").status_code == 200
    assert client.get(f"/api/v1/assignments?academic_group_id={group['id']}").status_code == 200


def test_assignment_invalid_foreign_keys_and_not_found(client):
    school = create_school(client)
    course = client.post(
        "/api/v1/courses",
        json={
            "code": "BTECH",
            "name": "BTech",
            "school_id": school["id"],
            "duration_years": 4,
            "total_semesters": 8,
        },
    ).json()
    payload = {
        "subject_id": 999,
        "course_id": course["id"],
        "academic_group_id": 999,
        "faculty_id": 999,
        "sessions_per_week": 1,
        "duration_periods": 1,
        "mode": "IN_PERSON",
    }
    assert client.post("/api/v1/assignments", json=payload).status_code == 404
    assert client.get("/api/v1/subjects/999").status_code == 404


def test_patch_validation_and_delete_behaviour(client):
    school = create_school(client)
    course = client.post(
        "/api/v1/courses",
        json={
            "code": "BTECH",
            "name": "BTech",
            "school_id": school["id"],
            "duration_years": 4,
            "total_semesters": 8,
        },
    ).json()
    group = client.post(
        "/api/v1/groups",
        json={"code": "G1", "name": "Group 1", "group_type": "GROUP", "course_id": course["id"]},
    ).json()
    assert (
        client.patch(
            f"/api/v1/groups/{group['id']}", json={"parent_group_id": group["id"]}
        ).status_code
        == 422
    )
    # Referenced schools cannot be deleted silently.
    assert client.delete(f"/api/v1/schools/{school['id']}").status_code == 409
