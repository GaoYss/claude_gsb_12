"""特种作业证书业务逻辑：登记、到期判定与提醒。"""

from datetime import timedelta

from sqlalchemy import and_, case, func, or_

from ..constants import CERT_EXPIRE_SOON_DAYS, CERT_TYPE
from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import Certificate, Person
from ..models.certificate import derive_validity
from ..utils.dates import today
from ..utils.sorting import parse_sort
from .base_service import BaseService


def deadline_column():
    """到期依据：复审日早于有效期时以复审日为准（跨 SQLite/PostgreSQL 兼容）。"""

    review = Certificate.review_date
    return case(
        (and_(review.isnot(None), review < Certificate.expire_date), review),
        else_=Certificate.expire_date,
    )


class CertificateService(BaseService):
    """特种作业证书登记与到期管理。"""

    model = Certificate
    label = "特种作业证书"
    # 证书编号采用发证机关编号，手工录入，不做自动生成
    code_field = "cert_no"

    @classmethod
    def generate_code(cls):
        return None

    SORTABLE = {
        "expire_date": Certificate.expire_date,
        "review_date": Certificate.review_date,
        "issue_date": Certificate.issue_date,
        "cert_no": Certificate.cert_no,
    }

    # ------------------------------------------------------------ 校验
    @classmethod
    def prepare_instance(cls, instance, payload):
        person_id = payload.get("person_id", instance.person_id)
        person = db.session.get(Person, person_id) if person_id else None
        if person is None:
            raise ValidationError("登记失败", details={"person_id": "持证人不存在"})

        cert_type = payload.get("cert_type", instance.cert_type)
        duplicate = (
            db.session.query(Certificate.id)
            .filter(
                Certificate.person_id == person_id,
                Certificate.cert_type == cert_type,
                Certificate.id != instance.id,
            )
            .first()
        )
        if duplicate:
            label = CERT_TYPE.label(cert_type)
            raise ConflictError(f"人员「{person.name}」已登记{label}，同类证书不能重复登记")

    # ------------------------------------------------------------ 查询
    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("person_id"):
            query = query.filter(Certificate.person_id == filters["person_id"])
        if filters.get("cert_type"):
            query = query.filter(Certificate.cert_type == filters["cert_type"])
        if filters.get("status"):
            query = query.filter(Certificate.status == filters["status"])
        if filters.get("expire_from"):
            query = query.filter(Certificate.expire_date >= filters["expire_from"])
        if filters.get("expire_to"):
            query = query.filter(Certificate.expire_date <= filters["expire_to"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Certificate.cert_no.like(like),
                    Certificate.issuer.like(like),
                    Person.name.like(like),
                    Person.employee_no.like(like),
                )
            )
        validity = filters.get("validity")
        if validity:
            current = today()
            cutoff = current + timedelta(days=CERT_EXPIRE_SOON_DAYS)
            deadline = deadline_column()
            if validity == "revoked":
                query = query.filter(Certificate.status == "revoked")
            else:
                query = query.filter(Certificate.status == "active")
                if validity == "valid":
                    query = query.filter(deadline > cutoff)
                elif validity == "expiring":
                    query = query.filter(deadline >= current, deadline <= cutoff)
                elif validity == "expired":
                    query = query.filter(deadline < current)
        return query

    @classmethod
    def list_certificates(cls, filters, args):
        query = db.session.query(Certificate).join(
            Person, Certificate.person_id == Person.id
        )
        query = cls._apply_filters(query, filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, deadline_column().asc())
        )

    @classmethod
    def serialize_row(cls, item):
        return item.to_dict()

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def change_status(cls, obj_id, status):
        """在册 / 已注销之间切换，注销后不再参与到期提醒与持证校验。"""

        cert = cls.get(obj_id)
        cert.status = status
        db.session.commit()
        return cert

    # ------------------------------------------------------------ 到期提醒
    @classmethod
    def expiring_certificates(cls, days=CERT_EXPIRE_SOON_DAYS, limit=50):
        """即将到期（或临近复审）的在册证书，按到期日升序。"""

        current = today()
        cutoff = current + timedelta(days=days)
        deadline = deadline_column()
        rows = (
            db.session.query(Certificate)
            .filter(Certificate.status == "active")
            .filter(deadline >= current, deadline <= cutoff)
            .order_by(deadline.asc())
            .limit(limit)
            .all()
        )
        return [item.to_dict() for item in rows]

    @classmethod
    def expired_certificates(cls, limit=50):
        """已过有效期或逾期未复审的在册证书。"""

        current = today()
        deadline = deadline_column()
        rows = (
            db.session.query(Certificate)
            .filter(Certificate.status == "active", deadline < current)
            .order_by(deadline.asc())
            .limit(limit)
            .all()
        )
        return [item.to_dict() for item in rows]

    @classmethod
    def reminder_summary(cls, days=CERT_EXPIRE_SOON_DAYS):
        """证书提醒汇总：已过期 / N 天内到期数量。"""

        current = today()
        cutoff = current + timedelta(days=days)
        deadline = deadline_column()
        expired, expiring = (
            db.session.query(
                func.coalesce(func.sum(case((deadline < current, 1), else_=0)), 0),
                func.coalesce(
                    func.sum(case((and_(deadline >= current, deadline <= cutoff), 1), else_=0)), 0
                ),
            )
            .filter(Certificate.status == "active")
            .one()
        )
        return {"expired_count": int(expired), "expiring_count": int(expiring), "days": days}

    @classmethod
    def summary(cls):
        """证书页面顶部汇总：在册、即将到期、已过期、已注销数量。"""

        current = today()
        rows = db.session.query(
            Certificate.status, Certificate.issue_date,
            Certificate.expire_date, Certificate.review_date,
        ).all()
        result = {
            "total": len(rows), "active": 0, "valid": 0,
            "expiring": 0, "expired": 0, "revoked": 0,
        }
        for status, issue_date, expire_date, review_date in rows:
            validity = derive_validity(status, issue_date, expire_date, review_date, current)
            result[validity] += 1
            if status == "active":
                result["active"] += 1
        result["days"] = CERT_EXPIRE_SOON_DAYS
        return result

    @classmethod
    def type_summary(cls):
        rows = (
            db.session.query(Certificate.cert_type, func.count(Certificate.id))
            .group_by(Certificate.cert_type)
            .all()
        )
        return [
            {"cert_type": cert_type, "cert_type_label": CERT_TYPE.label(cert_type), "count": count}
            for cert_type, count in rows
        ]

    # ------------------------------------------------------------ 持证校验
    @classmethod
    def check_assignees(cls, person_ids, cert_type, plan_date):
        """安排持证任务前的逐人预校验，不写库。"""

        from ..models import Person

        results = []
        if not cert_type or not person_ids:
            return results
        people = db.session.query(Person).filter(Person.id.in_(person_ids)).all()
        people_map = {person.id: person for person in people}
        for person_id in person_ids:
            person = people_map.get(person_id)
            if person is None:
                continue
            cert = (
                db.session.query(Certificate)
                .filter(Certificate.person_id == person_id, Certificate.cert_type == cert_type)
                .order_by(Certificate.expire_date.desc())
                .first()
            )
            results.append({
                "person_id": person_id,
                "person": person.to_brief(),
                "certificate": cert.to_dict() if cert else None,
                "valid": bool(cert and cert.is_valid_on(plan_date)),
            })
        return results
