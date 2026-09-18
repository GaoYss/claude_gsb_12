"""作业人员档案接口测试。"""

from datetime import date


def worker_payload(**overrides):
    payload = {
        "name": "王海涛",
        "team": "绿化一班",
        "position": "班长",
        "phone": "13800010001",
        "status": "active",
        "hired_date": "2020-05-01",
    }
    payload.update(overrides)
    return payload


def test_create_worker_generates_yearly_code(api):
    data = api.data(api.post("/api/v1/workers", worker_payload()), 201)
    assert data["employee_no"] == f"WK-{date.today():%Y}-0001"
    assert data["status_label"] == "在岗"
    assert data["certificate_count"] == 0


def test_create_worker_rejects_duplicate_code(api, make_worker):
    make_worker(employee_no="WK-2026-0099")
    response = api.post("/api/v1/workers", worker_payload(employee_no="WK-2026-0099"))
    assert response.status_code == 409


def test_worker_phone_pattern_validation(api):
    response = api.post("/api/v1/workers", worker_payload(phone="abc123"))
    assert response.status_code == 422
    assert "phone" in response.get_json()["data"]


def test_list_workers_filters_by_status_and_keyword(api, make_worker):
    make_worker(name="高大锤", team="应急班组", status="active")
    make_worker(name="高小锤", team="植保班", status="resigned")

    assert api.data(api.get("/api/v1/workers", status="active"))["meta"]["total"] == 1
    assert api.data(api.get("/api/v1/workers", keyword="应急"))["meta"]["total"] == 1
    assert api.data(api.get("/api/v1/workers", keyword="高"))["meta"]["total"] == 2


def test_worker_options_only_active(api, make_worker):
    make_worker(name="在岗张三", status="active")
    make_worker(name="离职李四", status="resigned")
    data = api.data(api.get("/api/v1/workers/options"))
    names = {item["name"] for item in data["items"]}
    assert "在岗张三" in names
    assert "离职李四" not in names


def test_worker_detail_includes_certificates_and_training(api, make_worker, make_certificate, make_training):
    worker = make_worker()
    make_certificate(worker=worker)
    make_training(workers=[worker])

    data = api.data(api.get(f"/api/v1/workers/{worker.id}"))
    assert data["certificate_count"] == 1
    assert data["valid_certificate_count"] == 1
    assert len(data["certificates"]) == 1
    assert len(data["training_records"]) == 1
    assert data["training_records"][0]["attendance"] == "attended"


def test_delete_worker_protected_when_related(api, make_worker, make_certificate):
    worker = make_worker()
    make_certificate(worker=worker)
    response = api.delete(f"/api/v1/workers/{worker.id}")
    assert response.status_code == 409
    assert response.get_json()["data"]["certificate"] == 1

    api.data(api.delete(f"/api/v1/workers/{worker.id}", force="true"))
    assert api.data(api.get("/api/v1/workers"))["meta"]["total"] == 0


def test_delete_plain_worker(api, make_worker):
    worker = make_worker()
    api.data(api.delete(f"/api/v1/workers/{worker.id}"))
    assert api.data(api.get("/api/v1/workers"))["meta"]["total"] == 0
