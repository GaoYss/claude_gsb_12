"""特种作业证书与持证上岗校验测试。"""

from datetime import date, timedelta


def cert_payload(worker_id, **overrides):
    payload = {
        "cert_no": "ZY-2026-0001",
        "worker_id": worker_id,
        "cert_type": "aerial",
        "issuing_authority": "杭州市应急管理局",
        "issue_date": "2024-01-01",
        "expire_date": (date.today() + timedelta(days=200)).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_register_certificate(api, make_worker):
    worker = make_worker()
    data = api.data(api.post("/api/v1/certificates", cert_payload(worker.id)), 201)
    assert data["status"] == "effective"
    assert data["days_to_expire"] == 200
    assert data["worker"]["name"] == worker.name
    assert data["cert_type_label"] == "高处作业（登高）"


def test_certificate_expire_date_must_be_after_issue_date(api, make_worker):
    worker = make_worker()
    response = api.post("/api/v1/certificates", cert_payload(
        worker.id, issue_date="2026-01-01", expire_date="2025-01-01"
    ))
    assert response.status_code == 422
    assert "expire_date" in response.get_json()["data"]


def test_certificate_requires_existing_worker(api):
    response = api.post("/api/v1/certificates", cert_payload(999))
    assert response.status_code == 422
    assert response.get_json()["data"] == {"worker_id": "持证人不存在"}


def test_certificate_status_expiring_and_expired(api, make_worker, make_certificate):
    make_certificate(cert_no="C-EXPIRED", expire_on=date.today() - timedelta(days=5))
    make_certificate(cert_no="C-SOON", expire_on=date.today() + timedelta(days=12))
    make_certificate(cert_no="C-FINE", expire_on=date.today() + timedelta(days=180))

    assert api.data(api.get("/api/v1/certificates", status="expired"))["meta"]["total"] == 1
    soon = api.data(api.get("/api/v1/certificates", status="expiring"))
    assert soon["meta"]["total"] == 1
    assert soon["items"][0]["cert_no"] == "C-SOON"
    assert api.data(api.get("/api/v1/certificates", status="effective"))["meta"]["total"] == 1


def test_certificate_reminders(api, make_worker, make_certificate):
    make_certificate(cert_no="C-EXPIRED", expire_on=date.today() - timedelta(days=3))
    make_certificate(cert_no="C-SOON", expire_on=date.today() + timedelta(days=8))
    make_certificate(cert_no="C-FINE", expire_on=date.today() + timedelta(days=400))

    data = api.data(api.get("/api/v1/certificates/reminders"))
    nos = {item["cert_no"] for item in data["expiring"]}
    expired_nos = {item["cert_no"] for item in data["expired"]}
    assert nos == {"C-SOON"}
    assert expired_nos == {"C-EXPIRED"}


def test_valid_check_endpoint(api, make_worker, make_certificate):
    worker = make_worker()
    make_certificate(worker=worker, expire_on=date.today() + timedelta(days=100))
    data = api.data(api.get("/api/v1/certificates/valid-check",
                            worker_id=worker.id, cert_type="aerial"))
    assert data["valid"] is True

    no_cert_worker = make_worker()
    data = api.data(api.get("/api/v1/certificates/valid-check",
                            worker_id=no_cert_worker.id, cert_type="aerial"))
    assert data["valid"] is False
    assert "未登记" in data["message"]


# ------------------------------------------------------- 任务派工校验
def task_with_workers(space_id, worker_ids, **overrides):
    payload = {
        "green_space_id": space_id,
        "title": "高空修剪作业",
        "task_type": "prune",
        "plan_date": (date.today() + timedelta(days=2)).isoformat(),
        "required_cert_type": "aerial",
        "worker_ids": worker_ids,
    }
    payload.update(overrides)
    return payload


def test_certified_task_accepts_valid_holder(api, make_space, make_worker, make_certificate):
    space = make_space()
    worker = make_worker()
    make_certificate(worker=worker, expire_on=date.today() + timedelta(days=100))
    data = api.data(api.post(
        "/api/v1/maintenance-tasks", task_with_workers(space.id, [worker.id])
    ), 201)
    assert data["requires_certificate"] is True
    assert data["worker_count"] == 1
    assert data["workers"][0]["worker"]["name"] == worker.name


def test_certified_task_rejects_expired_holder(api, make_space, make_worker, make_certificate):
    space = make_space()
    worker = make_worker()
    make_certificate(worker=worker, expire_on=date.today() - timedelta(days=1))
    response = api.post("/api/v1/maintenance-tasks", task_with_workers(space.id, [worker.id]))
    assert response.status_code == 409
    assert "过期" in response.get_json()["message"]


def test_certified_task_rejects_worker_without_certificate(api, make_space, make_worker):
    space = make_space()
    worker = make_worker()
    response = api.post("/api/v1/maintenance-tasks", task_with_workers(space.id, [worker.id]))
    assert response.status_code == 409
    assert "未登记" in response.get_json()["message"]


def test_cert_check_uses_plan_date(api, make_space, make_worker, make_certificate):
    """计划作业日期当天证书必须有效：当前有效但作业日已过期的也要拒绝。"""

    space = make_space()
    worker = make_worker()
    make_certificate(worker=worker, expire_on=date.today() + timedelta(days=5))
    response = api.post("/api/v1/maintenance-tasks", task_with_workers(
        space.id, [worker.id], plan_date=(date.today() + timedelta(days=20)).isoformat()
    ))
    assert response.status_code == 409


def test_certified_task_rejects_unknown_worker(api, make_space):
    space = make_space()
    response = api.post("/api/v1/maintenance-tasks", task_with_workers(space.id, [999]))
    assert response.status_code == 422
    assert "worker_ids" in response.get_json()["data"]


def test_uncertified_task_has_no_cert_requirement(api, make_space, make_worker):
    space = make_space()
    worker = make_worker()
    data = api.data(api.post("/api/v1/maintenance-tasks", {
        "green_space_id": space.id,
        "title": "日常保洁",
        "task_type": "clean",
        "plan_date": date.today().isoformat(),
        "worker_ids": [worker.id],
    }), 201)
    assert data["requires_certificate"] is False
    assert data["worker_count"] == 1


def test_task_worker_filter(api, make_space, make_worker, make_certificate):
    space = make_space()
    holder, other = make_worker(name="持证"), make_worker(name="无证")
    make_certificate(worker=holder, expire_on=date.today() + timedelta(days=100))
    api.data(api.post("/api/v1/maintenance-tasks", task_with_workers(space.id, [holder.id])), 201)
    api.data(api.post("/api/v1/maintenance-tasks", {
        "green_space_id": space.id,
        "title": "普通浇水",
        "task_type": "water",
        "plan_date": date.today().isoformat(),
        "worker_ids": [other.id],
    }), 201)

    assert api.data(api.get("/api/v1/maintenance-tasks", worker_id=holder.id))["meta"]["total"] == 1
    flagged = api.data(api.get("/api/v1/maintenance-tasks", requires_certificate="true"))
    assert flagged["meta"]["total"] == 1
