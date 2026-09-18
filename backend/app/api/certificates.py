"""特种作业证书接口。"""

from flask import Blueprint, request

from ..constants import CERT_TYPE
from ..schemas import (
    certificate_filters,
    validate_certificate,
    validate_certificate_status,
)
from ..services import CertificateService
from ..utils.dates import parse_date, today
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("certificates", __name__)


@bp.get("/certificates")
def list_certificates():
    filters = certificate_filters(request.args)
    page, page_size = parse_page_args()
    query = CertificateService.list_certificates(filters, request.args)
    data = paginate(query, page, page_size, serializer=CertificateService.serialize_row)
    data["summary"] = CertificateService.summary()
    return ok(data)


@bp.get("/certificates/reminders")
def certificate_reminders():
    """证书到期提醒：即将到期与已过期，支持 ?days= 自定义提前天数。"""

    try:
        days = int(request.args.get("days", 30))
    except (TypeError, ValueError):
        days = 30
    days = min(max(days, 1), 180)
    return ok({
        "summary": CertificateService.reminder_summary(days),
        "expiring": CertificateService.expiring_certificates(days),
        "expired": CertificateService.expired_certificates(),
    })


@bp.get("/certificates/check")
def check_person_certificates():
    """预校验：安排持证任务前，按作业日检查人员证书是否有效。

    传入 person_ids、cert_type、plan_date，返回每人的有效/无效结果，
    供前端在任务表单里实时提示，不写库。
    """

    cert_type = (request.args.get("cert_type") or "").strip()
    plan_date = today()
    if cert_type and not CERT_TYPE.has(cert_type):
        cert_type = None
    date_text = (request.args.get("plan_date") or "").strip()
    if date_text:
        try:
            plan_date = parse_date(date_text, "作业日期")
        except ValueError:
            plan_date = today()

    person_ids = _parse_ids(request.args.get("person_ids"))
    items = CertificateService.check_assignees(person_ids, cert_type, plan_date)
    return ok({"items": items, "plan_date": plan_date.isoformat()})


def _parse_ids(text):
    if not text:
        return []
    ids = []
    for part in str(text).split(","):
        part = part.strip()
        if part.isdigit():
            value = int(part)
            if value not in ids:
                ids.append(value)
    return ids[:200]


@bp.post("/certificates")
def create_certificate():
    payload = validate_certificate(json_body())
    cert = CertificateService.create(payload)
    return created(cert.to_dict(detail=True), message="特种作业证书登记成功")


@bp.get("/certificates/<int:cert_id>")
def get_certificate(cert_id):
    return ok(CertificateService.detail(cert_id))


@bp.patch("/certificates/<int:cert_id>/status")
def change_certificate_status(cert_id):
    """证书注销 / 恢复在册。"""

    payload = validate_certificate_status(json_body())
    cert = CertificateService.change_status(cert_id, payload["status"])
    return ok(cert.to_dict(detail=True),
              message="证书已注销" if cert.status == "revoked" else "证书已恢复在册")


@bp.put("/certificates/<int:cert_id>")
def update_certificate(cert_id):
    payload = validate_certificate(json_body())
    cert = CertificateService.update(cert_id, payload)
    return ok(cert.to_dict(detail=True), message="特种作业证书已更新")


@bp.delete("/certificates/<int:cert_id>")
def delete_certificate(cert_id):
    CertificateService.delete(cert_id)
    return ok(None, message="特种作业证书已注销/删除")
