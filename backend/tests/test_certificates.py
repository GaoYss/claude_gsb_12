"""特种作业证书接口、到期判定与提醒测试。"""

from datetime import date, timedelta


def cert_payload(person_id, **overrides):
    today_ = date.today()
    payload = {
        "person_id": person_id,
        "cert_no": "CERT-TEST-0001",
        "cert_type": "electrician_low",
        "issuer": "杭州市应急管理局",
        "issue_date": (today_ - timedelta(days=365)).isoformat(),
        "expire_date": (today_ + timedelta(days=300)).isoformat(),
    }
    payload.update(overrides)
    return payload


# ------------------------------------------------------------------ 登记
def test_create_certificate(api, make_person):
    person = make_person()
    data = api.data(api.post("/api/v1/certificates", cert_payload(person.id)), 201)
    assert data["cert_no"] == "CERT-TEST-0001"
    assert data["validity"] == "valid"
    assert data["validity_label"] == "有效"
    assert data["days_to_expire"] in range(299, 301)


def test_certificate_requires_person(api):
    response = api.post("/api/v1/certificates", cert_payload(99999))
    assert response.status_code == 422
    assert response.get_json()["data"] == {"person_id": "持证人不存在"}


def test_duplicate_cert_type_per_person_rejected(api, make_person):
    person = make_person()
    api.data(api.post("/api/v1/certificates", cert_payload(person.id)), 201)
    response = api.post(
        "/api/v1/certificates",
        cert_payload(person.id, cert_no="CERT-TEST-0002"),
    )
    assert response.status_code == 409
    assert "同类证书" in response.get_json()["message"]


def test_expire_date_before_issue_date_rejected(api, make_person):
    person = make_person()
    response = api.post(
        "/api/v1/certificates",
        cert_payload(person.id, issue_date="2026-05-01", expire_date="2026-04-01"),
    )
    assert response.status_code == 422
    assert "expire_date" in response.get_json()["data"]


def test_review_date_must_fit_certificate_window(api, make_person):
    person = make_person()
    bad = api.post("/api/v1/certificates", cert_payload(
        person.id, review_date="2030-01-01"))
    assert bad.status_code == 422
    good = api.post("/api/v1/certificates", cert_payload(
        person.id, cert_no="CERT-OK", review_date="2025-06-01",
        issue_date="2024-01-01", expire_date="2027-01-01"))
    assert good.status_code == 201


# ------------------------------------------------------------------ 时效
def test_validity_expiring_within_30_days(api, make_person):
    person = make_person()
    data = api.data(api.post("/api/v1/certificates", cert_payload(
        person.id, expire_date=(date.today() + timedelta(days=10)).isoformat())), 201)
    assert data["validity"] == "expiring"
    assert data["days_to_expire"] == 10


def test_exact_30_days_is_expiring(api, make_person):
    """第 30 天仍属于即将到期窗口（闭区间）。"""

    person = make_person()
    data = api.data(api.post("/api/v1/certificates", cert_payload(
        person.id, expire_date=(date.today() + timedelta(days=30)).isoformat())), 201)
    assert data["validity"] == "expiring"


def test_exact_31_days_is_valid(api, make_person):
    person = make_person()
    data = api.data(api.post("/api/v1/certificates", cert_payload(
        person.id, expire_date=(date.today() + timedelta(days=31)).isoformat())), 201)
    assert data["validity"] == "valid"


def test_expired_certificate(api, make_person):
    person = make_person()
    data = api.data(api.post("/api/v1/certificates", cert_payload(
        person.id,
        issue_date=(date.today() - timedelta(days=700)).isoformat(),
        expire_date=(date.today() - timedelta(days=5)).isoformat())), 201)
    assert data["validity"] == "expired"
    assert data["days_to_expire"] == -5


def test_review_date_earlier_than_expire_drives_expiry(api, make_person):
    """复审日早于有效期时，到期依据取较早的复审日。"""

    person = make_person()
    # 有效期还有 200 天，但 12 天后要复审 → 显示即将到期
    data = api.data(api.post("/api/v1/certificates", cert_payload(
        person.id,
        expire_date=(date.today() + timedelta(days=200)).isoformat(),
        review_date=(date.today() + timedelta(days=12)).isoformat())), 201)
    assert data["validity"] == "expiring"
    assert data["deadline"] == (date.today() + timedelta(days=12)).isoformat()
    assert data["days_to_expire"] == 12


def test_review_overdue_makes_cert_invalid_for_work(api, make_person):
    person = make_person()
    cert = api.data(api.post("/api/v1/certificates", cert_payload(
        person.id,
        expire_date=(date.today() + timedelta(days=200)).isoformat(),
        review_date=(date.today() - timedelta(days=1)).isoformat())), 201)
    assert cert["validity"] == "expired"
    # 作业日校验：复审逾期即失效
    response = api.get("/api/v1/certificates/check",
                       person_ids=str(person.id), cert_type="electrician_low",
                       plan_date=date.today().isoformat())
    result = api.data(response)
    assert result["items"][0]["valid"] is False


# ------------------------------------------------------------------ 列表/提醒
def test_list_filters_by_validity(api, make_person, make_certificate):
    today_ = date.today()
    p1 = make_person()
    p2 = make_person()
    p3 = make_person()
    make_certificate(person=p1, cert_no="V-1",
                     issue_date=today_ - timedelta(days=100),
                     expire_date=today_ + timedelta(days=200))
    make_certificate(person=p2, cert_no="E-1",
                     issue_date=today_ - timedelta(days=700),
                     expire_date=today_ + timedelta(days=8))
    make_certificate(person=p3, cert_no="X-1",
                     issue_date=today_ - timedelta(days=800),
                     expire_date=today_ - timedelta(days=2))

    assert api.data(api.get("/api/v1/certificates", validity="valid"))["meta"]["total"] == 1
    assert api.data(api.get("/api/v1/certificates", validity="expiring"))["meta"]["total"] == 1
    assert api.data(api.get("/api/v1/certificates", validity="expired"))["meta"]["total"] == 1


def test_list_filters_by_type_and_keyword(api, make_person, make_certificate):
    person = make_person(name="特殊人员")
    make_certificate(person=person, cert_type="height", cert_no="HT-001")
    assert api.data(api.get("/api/v1/certificates", cert_type="height"))["meta"]["total"] == 1
    assert api.data(api.get("/api/v1/certificates", keyword="特殊人员"))["meta"]["total"] == 1
    assert api.data(api.get("/api/v1/certificates", keyword="HT-001"))["meta"]["total"] == 1


def test_list_returns_summary(api, make_person, make_certificate):
    today_ = date.today()
    person = make_person()
    make_certificate(person=person,
                     issue_date=today_ - timedelta(days=700),
                     expire_date=today_ + timedelta(days=5))
    data = api.data(api.get("/api/v1/certificates"))
    assert data["summary"]["expiring"] == 1
    assert data["summary"]["active"] == 1


def test_reminders_endpoint(api, make_person, make_certificate):
    today_ = date.today()
    soon = make_person()
    late = make_person()
    make_certificate(person=soon, cert_no="SOON",
                     issue_date=today_ - timedelta(days=700),
                     expire_date=today_ + timedelta(days=9))
    make_certificate(person=late, cert_no="LATE",
                     issue_date=today_ - timedelta(days=900),
                     expire_date=today_ - timedelta(days=3))

    data = api.data(api.get("/api/v1/certificates/reminders"))
    assert data["summary"]["expiring_count"] == 1
    assert data["summary"]["expired_count"] == 1
    assert data["expiring"][0]["cert_no"] == "SOON"
    assert data["expired"][0]["cert_no"] == "LATE"


def test_check_endpoint_returns_per_person_result(api, make_person, make_certificate):
    today_ = date.today()
    valid_p = make_person()
    expiring_p = make_person()
    make_certificate(person=valid_p, cert_no="OK",
                     issue_date=today_ - timedelta(days=300),
                     expire_date=today_ + timedelta(days=300))
    make_certificate(person=expiring_p, cert_no="SHORT",
                     issue_date=today_ - timedelta(days=700),
                     expire_date=today_ + timedelta(days=10))

    data = api.data(api.get("/api/v1/certificates/check",
                            person_ids=f"{valid_p.id},{expiring_p.id}",
                            cert_type="electrician_low",
                            plan_date=(today_ + timedelta(days=5)).isoformat()))
    assert data["plan_date"] == (today_ + timedelta(days=5)).isoformat()
    by_id = {item["person_id"]: item for item in data["items"]}
    assert by_id[valid_p.id]["valid"] is True
    # 作业日（5 天后）仍在有效期（10 天）内 → 有效
    assert by_id[expiring_p.id]["valid"] is True

    # 作业日推迟到 15 天后 → 证书已过期，无效
    data2 = api.data(api.get("/api/v1/certificates/check",
                             person_ids=str(expiring_p.id),
                             cert_type="electrician_low",
                             plan_date=(today_ + timedelta(days=15)).isoformat()))
    assert data2["items"][0]["valid"] is False


def test_update_after_review_resets_validity(api, make_person, make_certificate):
    """复审通过后更新复审日期与有效期，证书恢复有效。"""

    today_ = date.today()
    person = make_person()
    cert = make_certificate(
        person=person,
        issue_date=today_ - timedelta(days=1000),
        expire_date=today_ + timedelta(days=200),
        review_date=today_ - timedelta(days=3),
    )
    assert cert.validity == "expired"

    payload = cert_payload(
        person.id,
        cert_no=cert.cert_no,
        issue_date=cert.issue_date.isoformat(),
        expire_date=(today_ + timedelta(days=800)).isoformat(),
        review_date=(today_ + timedelta(days=700)).isoformat(),
    )
    data = api.data(api.put(f"/api/v1/certificates/{cert.id}", payload))
    assert data["validity"] == "valid"
    assert data["days_to_expire"] == 700


def test_revoked_certificate(api, make_person, make_certificate):
    today_ = date.today()
    person = make_person()
    cert = make_certificate(person=person,
                            issue_date=today_ - timedelta(days=100),
                            expire_date=today_ + timedelta(days=300))
    data = api.data(api.put(f"/api/v1/certificates/{cert.id}", cert_payload(
        person.id, cert_no=cert.cert_no, status="revoked",
        issue_date=cert.issue_date.isoformat(),
        expire_date=cert.expire_date.isoformat())))
    assert data["validity"] == "revoked"
    assert data["days_to_expire"] is None
    assert api.data(api.get("/api/v1/certificates", validity="revoked"))["meta"]["total"] == 1
