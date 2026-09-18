"""人员档案接口与业务规则测试。"""

from datetime import date


def person_payload(employee_no="EMP0001", **overrides):
    payload = {
        "employee_no": employee_no,
        "name": "张三",
        "team": "绿化一班",
        "position": "绿化工",
        "phone": "13800010001",
        "status": "active",
        "entry_date": "2022-03-01",
    }
    payload.update(overrides)
    return payload


def test_create_person(api):
    data = api.data(api.post("/api/v1/persons", person_payload()), 201)
    assert data["employee_no"] == "EMP0001"
    assert data["name"] == "张三"
    assert data["status"] == "active"
    assert data["status_label"] == "在岗"


def test_employee_no_must_be_unique(api, make_person):
    make_person(employee_no="EMP0001")
    response = api.post("/api/v1/persons", person_payload())
    assert response.status_code == 409
    assert "已存在" in response.get_json()["message"]


def test_name_is_required(api):
    payload = person_payload(name="")
    response = api.post("/api/v1/persons", payload)
    assert response.status_code == 422
    assert "name" in response.get_json()["data"]


def test_invalid_phone_is_rejected(api):
    response = api.post("/api/v1/persons", person_payload(phone="abc"))
    assert response.status_code == 422
    assert "phone" in response.get_json()["data"]


def test_list_persons_with_filters(api, make_person):
    make_person(name="王电工", team="机修班", status="active")
    make_person(name="李离岗", team="机修班", status="resigned")
    make_person(name="赵绿化工", team="绿化班", status="active")

    assert api.data(api.get("/api/v1/persons"))["meta"]["total"] == 3
    assert api.data(api.get("/api/v1/persons", status="resigned"))["meta"]["total"] == 1
    assert api.data(api.get("/api/v1/persons", team="机修班"))["meta"]["total"] == 2
    result = api.data(api.get("/api/v1/persons", keyword="电工"))
    assert result["meta"]["total"] == 1
    assert result["items"][0]["name"] == "王电工"


def test_person_options_only_returns_active(api, make_person):
    make_person(name="在岗人员", status="active")
    make_person(name="离岗人员", status="resigned")
    data = api.data(api.get("/api/v1/persons/options"))
    names = [item["name"] for item in data["items"]]
    assert "在岗人员" in names
    assert "离岗人员" not in names

    # 筛选/补录场景显式要求包含离岗人员
    data_all = api.data(api.get("/api/v1/persons/options", include_inactive="true"))
    names_all = [item["name"] for item in data_all["items"]]
    assert "离岗人员" in names_all


def test_person_detail_includes_certificates_and_trainings(
    api, make_person, make_certificate, make_training
):
    person = make_person(name="吴国强", team="植保班")
    make_certificate(person=person, cert_type="pest_control")
    make_training(
        topic="农药安全使用培训",
        attendees=[{"person_id": person.id, "attendance": "present", "score": "92"}],
    )

    data = api.data(api.get(f"/api/v1/persons/{person.id}"))
    assert data["name"] == "吴国强"
    assert len(data["certificates"]) == 1
    assert len(data["trainings"]) == 1
    assert data["trainings"][0]["topic"] == "农药安全使用培训"


def test_delete_person_blocked_when_assigned(api, make_person, make_task, make_certificate):
    """已安排到任务的人员不能直接删除，应引导改为离岗。"""

    person = make_person(name="孙明华")
    make_certificate(person=person, cert_type="electrician_low")
    make_task(
        required_cert_type="electrician_low",
        assignee_ids=[person.id],
        plan_date=date(2026, 3, 10),
    )

    response = api.delete(f"/api/v1/persons/{person.id}")
    assert response.status_code == 409
    assert "养护任务" in response.get_json()["message"]

    # 改为离岗是允许的
    data = api.data(api.put(f"/api/v1/persons/{person.id}",
                            person_payload(person.employee_no, name="孙明华", status="resigned")))
    assert data["status"] == "resigned"


def test_delete_person_without_tasks_succeeds(api, make_person):
    person = make_person()
    response = api.delete(f"/api/v1/persons/{person.id}")
    assert response.status_code == 200
    assert api.data(api.get("/api/v1/persons"))["meta"]["total"] == 0


def test_delete_person_cascades_certificates_and_attendance(
    api, make_person, make_certificate, make_training
):
    """删除人员时其证书与培训签到一并清理，培训记录本身保留。"""

    from app.models import Certificate, TrainingAttendee, TrainingRecord

    person = make_person()
    make_certificate(person=person)
    make_training(attendees=[{"person_id": person.id, "attendance": "present"}])

    assert Certificate.query.count() == 1
    assert TrainingAttendee.query.count() == 1
    assert TrainingRecord.query.count() == 1

    assert api.delete(f"/api/v1/persons/{person.id}").status_code == 200

    assert Certificate.query.count() == 0
    assert TrainingAttendee.query.count() == 0
    # 培训记录保留
    assert TrainingRecord.query.count() == 1
    training = TrainingRecord.query.first()
    assert len(training.attendees) == 0


def test_list_includes_statistics(api, make_person, make_certificate, make_training):
    person = make_person()
    make_certificate(person=person, cert_type="height")
    make_training(attendees=[{"person_id": person.id, "attendance": "present"}])

    data = api.data(api.get("/api/v1/persons"))
    stats = data["items"][0]["statistics"]
    assert stats["certificate_count"] == 1
    assert stats["active_certificate_count"] == 1
    assert stats["training_count"] == 1
