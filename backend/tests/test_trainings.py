"""人员培训记录接口与业务规则测试。"""

from datetime import date


def training_payload(**overrides):
    payload = {
        "topic": "高处作业安全培训",
        "category": "special",
        "train_date": "2026-03-05",
        "location": "班组园地",
        "trainer": "王海涛",
        "duration_hours": 3,
        "content": "安全带佩戴与登高作业规范。",
        "attendees": [],
    }
    payload.update(overrides)
    return payload


def test_create_training_generates_daily_code_and_attendees(api, make_person):
    p1 = make_person(name="张三")
    p2 = make_person(name="李四")
    data = api.data(api.post("/api/v1/trainings", training_payload(attendees=[
        {"person_id": p1.id, "attendance": "present", "score": "92"},
        {"person_id": p2.id, "attendance": "leave", "score": None},
    ])), 201)

    assert data["training_no"] == f"TR-{date.today():%Y%m%d}-001"
    assert data["attendee_count"] == 2
    assert data["present_count"] == 1
    assert data["attendees"][0]["person"]["name"] == "张三"
    assert data["attendees"][0]["attendance_label"] == "已参加"
    assert data["attendees"][1]["attendance"] == "leave"


def test_topic_and_trainer_are_required(api):
    response = api.post("/api/v1/trainings", {"train_date": "2026-03-05"})
    assert response.status_code == 422
    details = response.get_json()["data"]
    assert "topic" in details
    assert "trainer" in details


def test_invalid_category_enum(api):
    response = api.post("/api/v1/trainings", training_payload(category="unknown"))
    assert response.status_code == 422
    assert "category" in response.get_json()["data"]


def test_attendee_person_must_exist(api, make_person):
    person = make_person()
    response = api.post("/api/v1/trainings", training_payload(attendees=[
        {"person_id": person.id}, {"person_id": 99999},
    ]))
    assert response.status_code == 422
    assert "attendees" in response.get_json()["data"]


def test_duplicate_attendee_is_deduplicated(api, make_person):
    person = make_person()
    data = api.data(api.post("/api/v1/trainings", training_payload(attendees=[
        {"person_id": person.id, "attendance": "present"},
        {"person_id": person.id, "attendance": "absent"},
    ])), 201)
    assert data["attendee_count"] == 1
    # 保留第一次出现的出席情况
    assert data["attendees"][0]["attendance"] == "present"


def test_invalid_attendance_enum(api, make_person):
    person = make_person()
    response = api.post("/api/v1/trainings", training_payload(attendees=[
        {"person_id": person.id, "attendance": "late"},
    ]))
    assert response.status_code == 422


def test_attendees_must_be_array(api):
    response = api.post("/api/v1/trainings", training_payload(attendees="nope"))
    assert response.status_code == 422


def test_update_training_replaces_attendees(api, make_person, make_training):
    p1 = make_person(name="张三")
    p2 = make_person(name="李四")
    training = make_training(attendees=[{"person_id": p1.id, "attendance": "present"}])

    data = api.data(api.put(f"/api/v1/trainings/{training.id}", training_payload(
        topic="改后的主题",
        attendees=[{"person_id": p2.id, "attendance": "absent"}],
    )))
    assert data["topic"] == "改后的主题"
    assert data["attendee_count"] == 1
    assert data["attendees"][0]["person"]["name"] == "李四"
    assert data["attendees"][0]["attendance"] == "absent"


def test_list_filters_and_summaries(api, make_person, make_training):
    p1 = make_person()
    make_training(category="safety", topic="安全生产培训",
                  attendees=[{"person_id": p1.id, "attendance": "present"}])
    make_training(category="prejob", topic="岗前培训", trainer="许老师", attendees=[])

    assert api.data(api.get("/api/v1/trainings"))["meta"]["total"] == 2
    assert api.data(api.get("/api/v1/trainings", category="safety"))["meta"]["total"] == 1
    assert api.data(api.get("/api/v1/trainings", person_id=p1.id))["meta"]["total"] == 1
    keyword = api.data(api.get("/api/v1/trainings", keyword="许老师"))
    assert keyword["meta"]["total"] == 1
    # 列表行只带人数，不嵌套人员明细
    row = api.data(api.get("/api/v1/trainings", category="safety"))["items"][0]
    assert row["attendee_count"] == 1
    assert "attendees" not in row
    categories = {item["category"] for item in api.data(api.get("/api/v1/trainings"))["summary"]["categories"]}
    assert categories == {"safety", "prejob"}


def test_delete_training(api, make_training):
    training = make_training()
    assert api.delete(f"/api/v1/trainings/{training.id}").status_code == 200
    assert api.data(api.get("/api/v1/trainings"))["meta"]["total"] == 0


def test_update_without_attendees_keeps_existing_roster(api, make_person, make_training):
    """更新培训主题等字段但未提交 attendees 时，原有参加人员名单保留。"""

    p1 = make_person()
    training = make_training(
        topic="原主题",
        attendees=[{"person_id": p1.id, "attendance": "present"}],
    )
    # 只更新主题，请求体不带 attendees
    data = api.data(api.put(f"/api/v1/trainings/{training.id}", {
        "topic": "新主题",
        "category": "safety",
        "train_date": "2026-03-05",
        "trainer": "王老师",
    }))
    assert data["topic"] == "新主题"
    assert data["attendee_count"] == 1
    assert data["attendees"][0]["person_id"] == p1.id
