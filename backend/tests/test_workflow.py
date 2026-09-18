"""跨模块端到端流程测试。"""

from datetime import date as date_cls

from app.services import CertificateService


def test_green_space_lifecycle_from_ledger_to_replacement(api):
    """绿地建档 → 任务登记 → 记录录入 → 绿植更换 → 档案与看板联动。"""

    space = api.data(api.post("/api/v1/green-spaces", {
        "name": "滨江公园樱花大道",
        "district": "滨江区",
        "green_type": "park",
        "maintenance_grade": "level1",
        "area_sqm": 23800,
        "manager": "林轶",
        "contact_phone": "0571-86608812",
        "established_date": "2018-03-20",
    }), 201)
    space_id = space["id"]

    task = api.data(api.post("/api/v1/maintenance-tasks", {
        "green_space_id": space_id,
        "title": "樱花树越冬修剪",
        "task_type": "prune",
        "plan_date": "2026-03-05",
        "priority": "high",
        "executor": "绿化一班",
    }), 201)
    assert task["status"] == "pending"

    record = api.data(api.post("/api/v1/maintenance-records", {
        "task_id": task["id"],
        "record_date": "2026-03-06",
        "work_content": "修剪染井吉野樱 46 株，清运枝条 3 车",
        "worker": "王海涛",
        "work_hours": 8,
        "weather": "sunny",
        "quality_result": "qualified",
    }), 201)
    assert record["green_space_id"] == space_id

    replacement = api.data(api.post("/api/v1/plant-replacements", {
        "green_space_id": space_id,
        "maintenance_record_id": record["id"],
        "plant_name": "染井吉野樱",
        "plant_category": "tree",
        "spec": "胸径 12-14cm",
        "quantity": 6,
        "unit": "plant",
        "reason": "dead",
        "old_plant_status": "dead",
        "replace_date": "2026-03-08",
        "supplier": "临安绿源苗圃",
        "unit_price": 680,
        "operator": "王海涛",
    }), 201)
    assert replacement["amount"] == 4080.0

    # 任务因合格记录自动完成
    task_detail = api.data(api.get(f"/api/v1/maintenance-tasks/{task['id']}"))
    assert task_detail["status"] == "completed"
    assert task_detail["progress"]["replacement_amount"] == 4080.0

    # 绿地档案汇总了一处绿地的全部养护数据
    profile = api.data(api.get(f"/api/v1/green-spaces/{space_id}/profile"))
    statistics = profile["statistics"]
    assert statistics["record_count"] == 1
    assert statistics["total_work_hours"] == 8.0
    assert statistics["replacement_quantity"] == 6.0
    assert statistics["replacement_amount"] == 4080.0
    assert statistics["task_status"]["completed"] == 1
    assert statistics["last_maintenance_date"] == "2026-03-06"
    assert profile["replacement_summary"][0]["reason"] == "dead"
    assert profile["recent_tasks"][0]["task_no"] == task["task_no"]
    assert profile["recent_records"][0]["record_no"] == record["record_no"]

    # 看板总览同步反映新增数据
    overview = api.data(api.get("/api/v1/statistics/overview"))
    assert overview["green_space"]["total"] == 1
    assert overview["task"]["by_status"]["completed"] == 1
    assert overview["replacement"]["total_amount"] == 4080.0

    # 台账列表带出统计列
    listing = api.data(api.get("/api/v1/green-spaces"))
    assert listing["items"][0]["statistics"]["record_count"] == 1
    assert listing["items"][0]["statistics"]["last_maintenance_date"] == "2026-03-06"


def test_task_and_record_codes_increase_in_sequence(api, make_space):
    space = make_space()
    task_payload = {
        "green_space_id": space.id,
        "title": "除草作业",
        "task_type": "weed",
        "plan_date": "2026-05-01",
    }
    first = api.data(api.post("/api/v1/maintenance-tasks", task_payload), 201)
    second = api.data(api.post("/api/v1/maintenance-tasks", task_payload), 201)
    assert first["task_no"].endswith("-001")
    assert second["task_no"].endswith("-002")

    record_payload = {
        "green_space_id": space.id,
        "record_date": "2026-05-02",
        "work_content": "清除绿篱内杂草约 800 平方米",
        "quality_result": "qualified",
    }
    first_record = api.data(api.post("/api/v1/maintenance-records", record_payload), 201)
    second_record = api.data(api.post("/api/v1/maintenance-records", record_payload), 201)
    assert first_record["record_no"].endswith("-001")
    assert second_record["record_no"].endswith("-002")


def test_demo_seed_produces_consistent_aggregates(api, seeded):
    """校验演示数据在多个聚合口径下保持一致。"""

    dashboard = api.data(api.get("/api/v1/statistics/dashboard"))
    overview = dashboard["overview"]
    assert overview["record"]["total"] == seeded["maintenance_record"]
    assert overview["replacement"]["total"] == seeded["plant_replacement"]
    assert overview["task"]["total"] == seeded["maintenance_task"]

    records = api.data(api.get("/api/v1/maintenance-records", page_size=100))
    assert records["meta"]["total"] == seeded["maintenance_record"]
    assert len(records["items"]) == seeded["maintenance_record"]

    spaces = api.data(api.get("/api/v1/green-spaces", page_size=100))
    total_records_from_spaces = sum(
        item["statistics"]["record_count"] for item in spaces["items"]
    )
    assert total_records_from_spaces == seeded["maintenance_record"]


def test_demo_seed_personnel_data_is_consistent(api, seeded):
    """演示数据的人员、培训、证书口径一致，持证任务的人员均持有效证书。"""

    persons = api.data(api.get("/api/v1/persons", page_size=100))
    assert persons["meta"]["total"] == seeded["person"]

    trainings = api.data(api.get("/api/v1/trainings", page_size=100))
    assert trainings["meta"]["total"] == seeded["training"]

    certificates = api.data(api.get("/api/v1/certificates", page_size=100))
    assert certificates["meta"]["total"] == seeded["certificate"]

    # 看板纳入证书提醒与人员培训汇总
    dashboard = api.data(api.get("/api/v1/statistics/dashboard"))
    personnel = dashboard["overview"]["personnel"]
    assert personnel["person_total"] == seeded["person"]
    assert personnel["training_total"] == seeded["training"]
    assert "cert_expiring_count" in personnel
    assert "certificates" in api.data(api.get("/api/v1/statistics/reminders"))

    # 演示数据中所有持证任务的作业人员，作业日均持对应有效证书
    cert_tasks = api.data(
        api.get("/api/v1/maintenance-tasks", cert_required="true", page_size=100)
    )
    assert cert_tasks["meta"]["total"] > 0
    for task in cert_tasks["items"]:
        plan_date = date_cls.fromisoformat(task["plan_date"])
        person_ids = [a["person_id"] for a in task["assignees"]]
        assert person_ids, task["task_no"]
        results = CertificateService.check_assignees(
            person_ids, task["required_cert_type"], plan_date
        )
        assert all(item["valid"] for item in results), task["task_no"]


def test_training_certificate_and_certified_task_workflow(api, make_space, make_person):
    """培训登记 → 证书登记 → 持证任务安排 → 到期后拒绝安排的完整流程。"""

    space = make_space()
    person = make_person(name="周永强", team="机修班")

    # 1. 登记一场特种作业培训，该人员参加
    training = api.data(api.post("/api/v1/trainings", {
        "topic": "叉车安全操作规程培训",
        "category": "special",
        "train_date": "2026-01-10",
        "trainer": "外聘讲师",
        "duration_hours": 4,
        "attendees": [{"person_id": person.id, "attendance": "present", "score": "95"}],
    }), 201)
    assert training["present_count"] == 1

    # 2. 登记叉车证，作业日在有效期内，任务安排通过
    cert = api.data(api.post("/api/v1/certificates", {
        "person_id": person.id,
        "cert_no": "CC-FLOW-001",
        "cert_type": "forklift",
        "issuer": "杭州市市场监督管理局",
        "issue_date": "2026-01-15",
        "expire_date": "2028-01-14",
    }), 201)
    assert cert["validity"] == "valid"

    task = api.data(api.post("/api/v1/maintenance-tasks", {
        "green_space_id": space.id,
        "title": "苗木卸车搬运",
        "task_type": "replant",
        "plan_date": "2026-03-20",
        "required_cert_type": "forklift",
        "assignee_ids": [person.id],
    }), 201)
    assert task["assignee_person_ids"] == [person.id]

    # 3. 把证书有效期改到作业日之前（模拟到期未复审），再安排应被拒绝
    api.data(api.put(f"/api/v1/certificates/{cert['id']}", {
        "person_id": person.id,
        "cert_no": "CC-FLOW-001",
        "cert_type": "forklift",
        "issue_date": "2024-01-15",
        "expire_date": "2026-03-01",
    }))

    blocked = api.post("/api/v1/maintenance-tasks", {
        "green_space_id": space.id,
        "title": "再次安排叉车作业",
        "task_type": "replant",
        "plan_date": "2026-03-20",
        "required_cert_type": "forklift",
        "assignee_ids": [person.id],
    })
    assert blocked.status_code == 409
    assert "持证上岗校验未通过" in blocked.get_json()["message"]

    # 4. 该证书进入已过期提醒
    reminders = api.data(api.get("/api/v1/certificates/reminders"))
    expired_nos = {item["cert_no"] for item in reminders["expired"]}
    assert "CC-FLOW-001" in expired_nos

    # 5. 人员档案能同时查到培训与证书
    detail = api.data(api.get(f"/api/v1/persons/{person.id}"))
    assert len(detail["trainings"]) == 1
    assert detail["certificates"][0]["validity"] == "expired"
