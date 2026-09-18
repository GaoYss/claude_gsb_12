"""测试夹具：内存 SQLite + 常用业务数据工厂。"""

import random
from datetime import date

import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def payload_of(response, expected_status=200):
    """断言状态码并取出统一响应中的 data。"""

    assert response.status_code == expected_status, response.get_data(as_text=True)
    body = response.get_json()
    assert body["success"] is (expected_status < 400)
    return body["data"]


@pytest.fixture()
def api(client):
    class Api:
        def get(self, path, **params):
            return client.get(path, query_string=params)

        def post(self, path, json=None):
            return client.post(path, json=json or {})

        def put(self, path, json=None):
            return client.put(path, json=json or {})

        def patch(self, path, json=None):
            return client.patch(path, json=json or {})

        def delete(self, path, **params):
            return client.delete(path, query_string=params)

        data = staticmethod(payload_of)

    return Api()


@pytest.fixture()
def make_space(app):
    from app.services import GreenSpaceService

    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        payload = {
            "name": f"测试绿地{counter['n']}",
            "district": "西湖区",
            "green_type": "park",
            "maintenance_grade": "level2",
            "area_sqm": 1200,
            "established_date": date(2015, 5, 1),
        }
        payload.update(overrides)
        return GreenSpaceService.create(payload)

    return _make


@pytest.fixture()
def make_task(make_space):
    from app.services import MaintenanceTaskService

    def _make(space=None, **overrides):
        space = space or make_space()
        payload = {
            "green_space_id": space.id,
            "title": "春季修剪作业",
            "task_type": "prune",
            "plan_date": date(2026, 3, 10),
            "priority": "medium",
            "executor": "绿化一班",
        }
        payload.update(overrides)
        return MaintenanceTaskService.create(payload)

    return _make


@pytest.fixture()
def make_record(make_space):
    from app.services import MaintenanceRecordService

    def _make(space=None, task=None, **overrides):
        if task is not None:
            space = task.green_space
        space = space or make_space()
        payload = {
            "green_space_id": space.id,
            "record_date": date(2026, 3, 12),
            "work_content": "修剪香樟下垂枝 32 株",
            "worker": "王海涛",
            "work_hours": 6,
            "quality_result": "qualified",
        }
        if task is not None:
            payload["task_id"] = task.id
            payload.pop("green_space_id")
        payload.update(overrides)
        return MaintenanceRecordService.create(payload)

    return _make


@pytest.fixture()
def make_replacement(make_space):
    from app.services import PlantReplacementService

    def _make(space=None, record=None, **overrides):
        if record is not None:
            space = record.green_space
        space = space or make_space()
        payload = {
            "green_space_id": space.id,
            "plant_name": "香樟",
            "plant_category": "tree",
            "quantity": 10,
            "unit": "plant",
            "reason": "dead",
            "replace_date": date(2026, 3, 15),
            "unit_price": 128.5,
        }
        if record is not None:
            payload["maintenance_record_id"] = record.id
        payload.update(overrides)
        return PlantReplacementService.create(payload)

    return _make


@pytest.fixture()
def make_person(app):
    from app.services import PersonService

    counter = {"n": 0}

    def _make(**overrides):
        counter["n"] += 1
        payload = {
            "employee_no": f"EMP{counter['n']:04d}",
            "name": f"测试人员{counter['n']}",
            "team": "绿化一班",
            "position": "绿化工",
            "status": "active",
            "entry_date": date(2022, 3, 1),
        }
        payload.update(overrides)
        return PersonService.create(payload)

    return _make


@pytest.fixture()
def make_certificate(make_person):
    from app.services import CertificateService

    def _make(person=None, cert_type="electrician_low", **overrides):
        person = person or make_person()
        payload = {
            "person_id": person.id,
            "cert_no": f"CERT-{cert_type}-{person.id}",
            "cert_type": cert_type,
            "issuer": "杭州市应急管理局",
            "issue_date": date(2024, 1, 1),
            "expire_date": date(2027, 1, 1),
        }
        payload.update(overrides)
        return CertificateService.create(payload)

    return _make


@pytest.fixture()
def make_training(make_person):
    from app.services import TrainingRecordService

    def _make(trainer="王老师", attendees=None, **overrides):
        payload = {
            "topic": "安全生产培训",
            "category": "safety",
            "train_date": date(2026, 3, 1),
            "location": "单位会议室",
            "trainer": trainer,
            "duration_hours": 4,
            "attendees": attendees or [],
        }
        payload.update(overrides)
        return TrainingRecordService.create(payload)

    return _make


@pytest.fixture()
def seeded(app):
    """写入演示数据（固定随机种子，保证断言稳定）。"""

    from app.cli import generate_demo_data

    return generate_demo_data(random.Random(20260913))
