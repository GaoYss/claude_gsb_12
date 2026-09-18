"""养护任务持证上岗校验测试。"""

from datetime import date, timedelta


def task_with_cert(space_id, person_ids, cert_type="electrician_low", plan_offset=5):
    return {
        "green_space_id": space_id,
        "title": "路灯检修作业",
        "task_type": "other",
        "plan_date": (date.today() + timedelta(days=plan_offset)).isoformat(),
        "priority": "high",
        "required_cert_type": cert_type,
        "assignee_ids": person_ids,
    }


def test_task_without_cert_requirement_accepts_anyone(api, make_space, make_person):
    space = make_space()
    person = make_person()
    data = api.data(api.post("/api/v1/maintenance-tasks", {
        "green_space_id": space.id,
        "title": "日常保洁",
        "task_type": "clean",
        "plan_date": date.today().isoformat(),
        "assignee_ids": [person.id],
    }), 201)
    assert data["assignee_person_ids"] == [person.id]
    assert data["required_cert_type"] is None


def test_cert_task_passes_with_valid_certificate(api, make_space, make_person, make_certificate):
    space = make_space()
    person = make_person()
    make_certificate(
        person=person,
        issue_date=date.today() - timedelta(days=300),
        expire_date=date.today() + timedelta(days=300),
    )
    data = api.data(api.post(
        "/api/v1/maintenance-tasks", task_with_cert(space.id, [person.id])), 201)
    assert data["required_cert_type"] == "electrician_low"
    assert data["assignees"][0]["person"]["name"] == person.name


def test_cert_task_rejects_person_without_certificate(api, make_space, make_person):
    space = make_space()
    person = make_person()
    response = api.post(
        "/api/v1/maintenance-tasks", task_with_cert(space.id, [person.id]))
    assert response.status_code == 409
    message = response.get_json()["message"]
    assert "持证上岗校验未通过" in message
    assert person.name in message
    assert "未持有" in message


def test_cert_task_rejects_expired_certificate(api, make_space, make_person, make_certificate):
    space = make_space()
    person = make_person()
    make_certificate(
        person=person,
        issue_date=date.today() - timedelta(days=900),
        expire_date=date.today() - timedelta(days=2),
    )
    response = api.post(
        "/api/v1/maintenance-tasks", task_with_cert(space.id, [person.id]))
    assert response.status_code == 409
    assert "有效期至" in response.get_json()["message"]


def test_cert_task_rejects_certificate_expiring_before_work_date(
    api, make_space, make_person, make_certificate
):
    """证书在安排时虽未过期，但作业日晚于有效期 → 拒绝。"""

    space = make_space()
    person = make_person()
    make_certificate(
        person=person,
        issue_date=date.today() - timedelta(days=700),
        expire_date=date.today() + timedelta(days=10),
    )
    response = api.post(
        "/api/v1/maintenance-tasks", task_with_cert(space.id, [person.id], plan_offset=20))
    assert response.status_code == 409
    assert "早于作业日" in response.get_json()["message"]


def test_cert_task_rejects_overdue_review(api, make_space, make_person, make_certificate):
    """有效期内但复审逾期的证书不得上岗。"""

    space = make_space()
    person = make_person()
    make_certificate(
        person=person,
        issue_date=date.today() - timedelta(days=1000),
        expire_date=date.today() + timedelta(days=200),
        review_date=date.today() - timedelta(days=5),
    )
    response = api.post(
        "/api/v1/maintenance-tasks", task_with_cert(space.id, [person.id]))
    assert response.status_code == 409
    assert "复审" in response.get_json()["message"]


def test_cert_task_requires_assignees(api, make_space):
    space = make_space()
    response = api.post("/api/v1/maintenance-tasks", task_with_cert(space.id, []))
    assert response.status_code == 409
    assert "请先指定" in response.get_json()["message"]


def test_cert_must_match_required_type(api, make_space, make_person, make_certificate):
    """持有的是高处作业证，任务要求低压电工证 → 拒绝。"""

    space = make_space()
    person = make_person()
    make_certificate(
        person=person,
        cert_type="height",
        issue_date=date.today() - timedelta(days=300),
        expire_date=date.today() + timedelta(days=300),
    )
    response = api.post(
        "/api/v1/maintenance-tasks",
        task_with_cert(space.id, [person.id], cert_type="electrician_low"))
    assert response.status_code == 409
    assert "未持有低压电工作业" in response.get_json()["message"]


def test_starting_task_rechecks_certificates(
    api, make_space, make_person, make_certificate, make_task
):
    """任务登记时证书有效；计划作业日已过有效期时，开工（进行中）仍会被拦截。"""

    space = make_space()
    person = make_person()
    make_certificate(
        person=person,
        issue_date=date.today() - timedelta(days=700),
        expire_date=date.today() + timedelta(days=10),
    )
    task = make_task(
        space=space,
        title="路灯检修",
        task_type="other",
        plan_date=date.today() + timedelta(days=8),
        required_cert_type="electrician_low",
        assignee_ids=[person.id],
    )
    # 计划作业日在有效期内 → 开工通过
    data = api.data(api.patch(
        f"/api/v1/maintenance-tasks/{task.id}/status", {"status": "in_progress"}))
    assert data["status"] == "in_progress"


def test_update_plan_date_rechecks_certificates(
    api, make_space, make_person, make_certificate, make_task
):
    """把作业日期改到证书失效之后，更新任务应被拒绝。"""

    space = make_space()
    person = make_person()
    make_certificate(
        person=person,
        issue_date=date.today() - timedelta(days=700),
        expire_date=date.today() + timedelta(days=10),
    )
    task = make_task(
        space=space,
        title="路灯检修",
        task_type="other",
        plan_date=date.today() + timedelta(days=5),
        required_cert_type="electrician_low",
        assignee_ids=[person.id],
    )
    response = api.put(f"/api/v1/maintenance-tasks/{task.id}", {
        "green_space_id": space.id,
        "title": "路灯检修",
        "task_type": "other",
        "plan_date": (date.today() + timedelta(days=30)).isoformat(),
        "required_cert_type": "electrician_low",
        "assignee_ids": [person.id],
    })
    assert response.status_code == 409


def test_unknown_assignee_is_rejected(api, make_space):
    space = make_space()
    response = api.post(
        "/api/v1/maintenance-tasks", task_with_cert(space.id, [99999]))
    assert response.status_code == 422
    assert "assignee_ids" in response.get_json()["data"]


def test_resigned_person_cannot_be_assigned(api, make_space, make_person):
    space = make_space()
    person = make_person(status="resigned")
    response = api.post("/api/v1/maintenance-tasks", {
        "green_space_id": space.id,
        "title": "保洁",
        "task_type": "clean",
        "plan_date": date.today().isoformat(),
        "assignee_ids": [person.id],
    })
    assert response.status_code == 409
    assert "离岗" in response.get_json()["message"]


def test_task_list_filters_cert_required(api, make_space, make_person, make_task, make_certificate):
    space = make_space()
    person = make_person()
    make_certificate(person=person)
    make_task(space=space, required_cert_type="electrician_low", assignee_ids=[person.id])
    make_task(space=space, title="普通保洁", task_type="clean")

    data = api.data(api.get("/api/v1/maintenance-tasks", cert_required="true"))
    assert data["meta"]["total"] == 1
    assert data["items"][0]["required_cert_type"] == "electrician_low"
