"""特种作业证书接口。"""

from flask import Blueprint, request

from ..constants import CERT_EXPIRY_WARNING_DAYS
from ..errors import BadRequestError
from ..extensions import db
from ..models import Worker
from ..schemas import certificate_filters, validate_certificate
from ..services import CertificateService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("certificates", __name__)


def _warning_days():
    try:
        days = int(request.args.get("warning_days", CERT_EXPIRY_WARNING_DAYS))
    except (TypeError, ValueError):
        days = CERT_EXPIRY_WARNING_DAYS
    return min(max(days, 1), 365)


@bp.get("/certificates")
def list_certificates():
    filters = certificate_filters(request.args)
    page, page_size = parse_page_args()
    query = CertificateService.list_certificates(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = CertificateService.status_summary()
    return ok(data)


@bp.get("/certificates/reminders")
def certificate_reminders():
    """到期提醒：临近到期与已过期证书。"""

    days = _warning_days()
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    return ok(CertificateService.reminders(days, min(max(limit, 1), 200)))


@bp.get("/certificates/valid-check")
def valid_check():
    """派工前的持证校验预览：?worker_id=&cert_type="""

    worker_id = request.args.get("worker_id", type=int)
    cert_type = (request.args.get("cert_type") or "").strip()
    if not worker_id or not cert_type:
        raise BadRequestError("请提供 worker_id 与 cert_type")
    worker = db.session.get(Worker, worker_id)
    if worker is None:
        raise BadRequestError("作业人员不存在")
    problem = CertificateService.check_assignment(worker, cert_type)
    return ok({"valid": problem is None, "message": problem or "证书在有效期内"})


@bp.post("/certificates")
def create_certificate():
    payload = validate_certificate(json_body())
    certificate = CertificateService.create(payload)
    return created(certificate.to_dict(detail=True), message="证书登记成功")


@bp.get("/certificates/<int:certificate_id>")
def get_certificate(certificate_id):
    return ok(CertificateService.detail(certificate_id))


@bp.put("/certificates/<int:certificate_id>")
def update_certificate(certificate_id):
    payload = validate_certificate(json_body())
    certificate = CertificateService.update(certificate_id, payload)
    return ok(certificate.to_dict(detail=True), message="证书信息已更新")


@bp.delete("/certificates/<int:certificate_id>")
def delete_certificate(certificate_id):
    CertificateService.delete(certificate_id)
    return ok(None, message="证书已删除")
