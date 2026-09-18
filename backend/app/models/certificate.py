"""特种作业证书模型。"""

from datetime import timedelta

from ..constants import (
    CERT_EXPIRE_SOON_DAYS,
    CERT_TYPE,
    CERTIFICATE_STATUS,
    CERTIFICATE_VALIDITY,
)
from ..extensions import db
from ..utils.dates import format_date, format_datetime, today
from .mixins import TimestampMixin


def derive_validity(status, issue_date, expire_date, review_date=None, on_date=None):
    """按登记状态与日期派生证书时效：有效 / 即将到期 / 已过期 / 已注销。

    复审日早于有效期截止日时，以最近的复审日作为到期提醒依据；
    复审通过后会更新复审日，不影响证书本身有效期。
    """

    if status == "revoked":
        return "revoked"
    current = on_date or today()
    deadline = expire_date
    if review_date and (deadline is None or review_date < deadline):
        deadline = review_date
    if deadline is None:
        # 未登记有效期/复审日的在册证书视为有效，仅无法给出到期提醒
        return "valid"
    if deadline < current:
        return "expired"
    if deadline <= current + timedelta(days=CERT_EXPIRE_SOON_DAYS):
        return "expiring"
    return "valid"


class Certificate(TimestampMixin, db.Model):
    """特种作业操作证 / 上岗证：登记类型、编号与有效期，到期前提醒。"""

    __tablename__ = "certificate"
    __table_args__ = (
        db.UniqueConstraint("person_id", "cert_type", name="uq_person_cert_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    cert_no = db.Column(db.String(64), nullable=False, unique=True, index=True)
    person_id = db.Column(
        db.Integer,
        db.ForeignKey("person.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cert_type = db.Column(db.String(32), nullable=False, index=True)
    issuer = db.Column(db.String(128))
    issue_date = db.Column(db.Date, nullable=False)
    expire_date = db.Column(db.Date, nullable=False, index=True)
    review_date = db.Column(db.Date, index=True)
    status = db.Column(db.String(16), nullable=False, default="active", index=True)
    remark = db.Column(db.Text)

    person = db.relationship("Person", back_populates="certificates", lazy="joined")

    @property
    def deadline(self):
        """到期提醒依据：复审日与有效期截止日中较早的一个。"""

        if self.review_date and (self.expire_date is None or self.review_date < self.expire_date):
            return self.review_date
        return self.expire_date

    @property
    def validity(self):
        return derive_validity(
            self.status, self.issue_date, self.expire_date, self.review_date
        )

    @property
    def days_to_expire(self):
        """距到期（或复审日）剩余天数，已过期为负数；已注销或无期限返回 None。"""

        if self.status == "revoked":
            return None
        deadline = self.deadline
        if deadline is None:
            return None
        return (deadline - today()).days

    def is_valid_on(self, on_date):
        """作业日当天是否可持证上岗。

        需同时满足：在册、已发证、未过有效期，且未错过复审日
        （特种作业证逾期未复审即失效，复审通过后更新复审日）。
        """

        if self.status != "active":
            return False
        if self.issue_date and on_date < self.issue_date:
            return False
        if self.expire_date and on_date > self.expire_date:
            return False
        if self.review_date and on_date > self.review_date:
            return False
        return True

    def to_dict(self, detail=False):
        validity = self.validity
        days = self.days_to_expire
        data = {
            "id": self.id,
            "cert_no": self.cert_no,
            "person_id": self.person_id,
            "person": self.person.to_brief() if self.person else None,
            "cert_type": self.cert_type,
            "cert_type_label": CERT_TYPE.label(self.cert_type),
            "issuer": self.issuer,
            "issue_date": format_date(self.issue_date),
            "expire_date": format_date(self.expire_date),
            "review_date": format_date(self.review_date),
            "status": self.status,
            "status_label": CERTIFICATE_STATUS.label(self.status),
            "validity": validity,
            "validity_label": CERTIFICATE_VALIDITY.label(validity),
            "days_to_expire": days,
            "deadline": format_date(self.deadline),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
