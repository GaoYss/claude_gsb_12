"""人员培训接口测试。"""

from datetime import date


def session_payload(workers, **overrides):
    payload = {
        "topic": "高大乔木修剪与高空作业安全",
        "category": "skill",
        "train_date": "2026-03-01",
        "duration_hours": 3,
        "trainer": "冯安全",
        "location": "运河文化公园现场",
        "attendees": [
            {"worker_id": person.id, "attendance": "attended", "result": "qualified", "score": 90}
            for person in workers
        ],
    }
    payload.update(overrides)
    return payload


def test_create_training_generates_daily_code(api, make_worker):
    worker = make_worker()
    data = api.data(api.post("/api/v1/training-sessions", session_payload([worker])), 201)
    assert data["session_no"] == f"TR-{date.today():%Y%m%d}-001"
    assert data["attendee_count"] == 1
    assert data["attended_count"] == 1
    assert data["qualified_count"] == 1
    assert data["attendees"][0]["worker"]["name"] == worker.name


def test_create_training_without_attendees(api):
    data = api.data(api.post("/api/v1/training-sessions", {
        "topic": "安全例会",
        "category": "safety",
        "train_date": "2026-03-02",
        "trainer": "冯安全",
    }), 201)
    assert data["attendee_count"] == 0


def test_training_attendee_field_errors_have_indexed_keys(api, make_worker):
    worker = make_worker()
    payload = session_payload([worker])
    payload["attendees"] = [{"worker_id": worker.id, "result": "bad_value"}]
    response = api.post("/api/v1/training-sessions", payload)
    assert response.status_code == 422
    assert "attendees[0].result" in response.get_json()["data"]


def test_training_rejects_unknown_and_duplicate_attendee(api, make_worker):
    worker = make_worker()
    payload = session_payload([worker])
    payload["attendees"] = [{"worker_id": 999}]
    response = api.post("/api/v1/training-sessions", payload)
    assert response.status_code == 422
    assert "参加人员不存在" in response.get_json()["data"]["attendees"]

    payload["attendees"] = [{"worker_id": worker.id}, {"worker_id": worker.id}]
    response = api.post("/api/v1/training-sessions", payload)
    assert response.status_code == 422
    assert "参加人员重复" in response.get_json()["data"]["attendees"]


def test_leave_attendance_forces_exempt_result(api, make_worker):
    worker = make_worker()
    data = api.data(api.post("/api/v1/training-sessions", session_payload(
        [worker], attendees=[{"worker_id": worker.id, "attendance": "leave", "result": "qualified"}]
    )), 201)
    assert data["attendees"][0]["attendance"] == "leave"
    assert data["attendees"][0]["result"] == "exempt"


def test_update_training_replaces_attendees(api, make_worker, make_training):
    first, second = make_worker(name="甲"), make_worker(name="乙")
    session = make_training(workers=[first])
    api.data(api.put(f"/api/v1/training-sessions/{session.id}", session_payload(
        [second], topic="更新后的主题"
    )))
    data = api.data(api.get(f"/api/v1/training-sessions/{session.id}"))
    assert data["topic"] == "更新后的主题"
    assert [item["worker_id"] for item in data["attendees"]] == [second.id]


def test_list_training_filters_by_category_worker_and_date(api, make_worker, make_training):
    worker = make_worker()
    make_training(workers=[worker], category="safety", train_date=date(2026, 1, 10))
    make_training(category="pest", train_date=date(2026, 5, 10))

    assert api.data(api.get("/api/v1/training-sessions", category="safety"))["meta"]["total"] == 1
    assert api.data(api.get("/api/v1/training-sessions", worker_id=worker.id))["meta"]["total"] == 1
    listing = api.data(api.get(
        "/api/v1/training-sessions", date_from="2026-04-01", date_to="2026-06-01"
    ))
    assert listing["meta"]["total"] == 1


def test_training_summary_counts(api, make_worker, make_training):
    first, second = make_worker(name="甲"), make_worker(name="乙")
    make_training(workers=[first], attendees=[
        {"worker_id": first.id, "attendance": "attended", "result": "qualified", "score": 88},
    ])
    make_training(workers=[second], attendees=[
        {"worker_id": second.id, "attendance": "leave", "result": "exempt"},
    ])
    data = api.data(api.get("/api/v1/training-sessions"))
    assert data["summary"]["session_count"] == 2
    assert data["summary"]["attendee_count"] == 2
    assert data["summary"]["attended_count"] == 1
    assert data["summary"]["qualified_count"] == 1
