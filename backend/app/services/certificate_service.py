"""特种作业证书业务逻辑：登记、到期提醒与持证校验。"""

from datetime import timedelta

from sqlalchemy import func, or_

from ..constants import CERT_EXPIRY_WARNING_DAYS
from ..errors import ValidationError
from ..extensions import db
from ..models import Certificate, Worker
from ..utils.dates import today
from ..utils.sorting import parse_sort
from .base_service import BaseService


class CertificateService(BaseService):
    """特种作业证书台账。"""

    model = Certificate
    label = "特种作业证书"

    SORTABLE = {
        "expire_date": Certificate.expire_date,
        "issue_date": Certificate.issue_date,
        "cert_no": Certificate.cert_no,
    }

    # ------------------------------------------------------------ 写入校验
    @classmethod
    def prepare_instance(cls, instance, payload):
        worker_id = payload.get("worker_id", instance.worker_id)
        worker = db.session.get(Worker, worker_id) if worker_id else None
        if worker is None:
            raise ValidationError("登记失败", details={"worker_id": "持证人不存在"})

        issue_date = payload.get("issue_date", instance.issue_date)
        expire_date = payload.get("expire_date", instance.expire_date)
        if issue_date and expire_date and expire_date <= issue_date:
            raise ValidationError(
                "登记失败", details={"expire_date": "有效期至必须晚于发证日期"}
            )

    # ------------------------------------------------------------ 持证校验
    @staticmethod
    def valid_certificate(worker_id, cert_type, on_date=None):
        """返回某人在指定日期持有的某类有效证书；没有则返回 None。"""

        current = on_date or today()
        return (
            db.session.query(Certificate)
            .filter(
                Certificate.worker_id == worker_id,
                Certificate.cert_type == cert_type,
                Certificate.issue_date <= current,
                Certificate.expire_date >= current,
            )
            .order_by(Certificate.expire_date.desc())
            .first()
        )

    @classmethod
    def check_assignment(cls, worker, cert_type, on_date=None):
        """派工前逐人校验证书，返回问题说明；证书有效返回 None。"""

        current = on_date or today()
        cert = cls.valid_certificate(worker.id, cert_type, current)
        if cert is not None:
            return None
        existing = (
            db.session.query(Certificate)
            .filter(Certificate.worker_id == worker.id, Certificate.cert_type == cert_type)
            .order_by(Certificate.expire_date.desc())
            .first()
        )
        if existing is None:
            return f"{worker.name} 未登记「{cert_type}」证书，不得安排持证作业"
        if existing.issue_date > current:
            return f"{worker.name} 的证书 {existing.cert_no} 尚未生效（{existing.issue_date}）"
        return f"{worker.name} 的证书 {existing.cert_no} 已于 {existing.expire_date} 过期，不得安排持证作业"

    # ------------------------------------------------------------ 到期提醒
    @staticmethod
    def expiring_certificates(warning_days=CERT_EXPIRY_WARNING_DAYS, limit=50):
        """临近到期（未过期且在预警窗口内）的证书，按到期日升序。"""

        current = today()
        rows = (
            db.session.query(Certificate)
            .filter(
                Certificate.expire_date >= current,
                Certificate.expire_date <= current + timedelta(days=warning_days),
            )
            .order_by(Certificate.expire_date.asc())
            .limit(limit)
            .all()
        )
        return [item.to_dict() for item in rows]

    @staticmethod
    def expired_certificates(limit=50):
        """已过期的证书，按过期最久优先。"""

        rows = (
            db.session.query(Certificate)
            .filter(Certificate.expire_date < today())
            .order_by(Certificate.expire_date.asc())
            .limit(limit)
            .all()
        )
        return [item.to_dict() for item in rows]

    @classmethod
    def reminders(cls, warning_days=CERT_EXPIRY_WARNING_DAYS, limit=50):
        return {
            "warning_days": warning_days,
            "expiring": cls.expiring_certificates(warning_days, limit),
            "expired": cls.expired_certificates(limit),
        }

    # ------------------------------------------------------------ 列表查询
    @staticmethod
    def _apply_filters(query, filters):
        current = today()
        if filters.get("worker_id"):
            query = query.filter(Certificate.worker_id == filters["worker_id"])
        if filters.get("cert_type"):
            query = query.filter(Certificate.cert_type == filters["cert_type"])
        if filters.get("status") == "effective":
            query = query.filter(
                Certificate.expire_date > current + timedelta(days=CERT_EXPIRY_WARNING_DAYS)
            )
        elif filters.get("status") == "expiring":
            query = query.filter(
                Certificate.expire_date >= current,
                Certificate.expire_date <= current + timedelta(days=CERT_EXPIRY_WARNING_DAYS),
            )
        elif filters.get("status") == "expired":
            query = query.filter(Certificate.expire_date < current)
        if filters.get("date_from"):
            query = query.filter(Certificate.expire_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(Certificate.expire_date <= filters["date_to"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.join(Worker).filter(
                or_(
                    Certificate.cert_no.like(like),
                    Worker.name.like(like),
                    Worker.employee_no.like(like),
                    Certificate.issuing_authority.like(like),
                )
            )
        return query

    @classmethod
    def list_certificates(cls, filters, args):
        query = cls._apply_filters(db.session.query(Certificate), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, Certificate.expire_date.asc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def status_summary(cls, warning_days=CERT_EXPIRY_WARNING_DAYS):
        current = today()
        rows = (
            db.session.query(
                func.sum(
                    db.case((Certificate.expire_date < current, 1), else_=0)
                ),
                func.sum(
                    db.case(
                        (Certificate.expire_date.between(
                            current, current + timedelta(days=warning_days)
                        ), 1),
                        else_=0,
                    )
                ),
                func.count(Certificate.id),
            ).one()
        )
        expired, expiring, total = (int(value or 0) for value in rows)
        return {
            "total": total,
            "effective": total - expired - expiring,
            "expiring": expiring,
            "expired": expired,
            "warning_days": warning_days,
        }
