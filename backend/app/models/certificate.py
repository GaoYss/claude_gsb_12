"""特种作业证书模型。"""

from datetime import timedelta

from ..constants import CERTIFICATE_TYPE, CERT_EXPIRY_WARNING_DAYS
from ..extensions import db
from ..utils.dates import format_date, format_datetime, today
from .mixins import TimestampMixin


class Certificate(TimestampMixin, db.Model):
    """特种作业操作证：一人一证，登记类型、编号与有效期，到期前自动预警。"""

    __tablename__ = "certificate"

    id = db.Column(db.Integer, primary_key=True)
    cert_no = db.Column(db.String(64), nullable=False, unique=True, index=True)
    worker_id = db.Column(
        db.Integer, db.ForeignKey("worker.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cert_type = db.Column(db.String(32), nullable=False, index=True)
    issuing_authority = db.Column(db.String(128))
    issue_date = db.Column(db.Date, nullable=False)
    expire_date = db.Column(db.Date, nullable=False, index=True)
    remark = db.Column(db.Text)

    worker = db.relationship("Worker", back_populates="certificates", lazy="joined")

    @property
    def days_to_expire(self):
        """距离到期的天数；已到期为负数。"""

        return (self.expire_date - today()).days

    @property
    def is_valid(self):
        """证书在有效期内（含临近到期，临近到期仍然有效，只是需要安排复审）。"""

        return self.expire_date >= today()

    @property
    def is_expiring(self):
        """已进入预警窗口但尚未过期。"""

        current = today()
        return current <= self.expire_date <= current + timedelta(days=CERT_EXPIRY_WARNING_DAYS)

    @property
    def status(self):
        """effective 有效 / expiring 临近到期 / expired 已过期。"""

        if self.expire_date < today():
            return "expired"
        if self.is_expiring:
            return "expiring"
        return "effective"

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "cert_no": self.cert_no,
            "worker_id": self.worker_id,
            "worker": self.worker.to_brief() if self.worker else None,
            "cert_type": self.cert_type,
            "cert_type_label": CERTIFICATE_TYPE.label(self.cert_type),
            "issuing_authority": self.issuing_authority,
            "issue_date": format_date(self.issue_date),
            "expire_date": format_date(self.expire_date),
            "status": self.status,
            "days_to_expire": self.days_to_expire,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
