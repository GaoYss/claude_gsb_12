"""作业人员档案模型。"""

from ..constants import WORKER_STATUS
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from .mixins import TimestampMixin


class Worker(TimestampMixin, db.Model):
    """作业人员：培训记录、证书与任务派工都围绕人员建档。"""

    __tablename__ = "worker"

    id = db.Column(db.Integer, primary_key=True)
    employee_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    gender = db.Column(db.String(8))
    phone = db.Column(db.String(24))
    team = db.Column(db.String(64), index=True)
    position = db.Column(db.String(64))
    status = db.Column(db.String(16), nullable=False, default="active", index=True)
    hired_date = db.Column(db.Date)
    remark = db.Column(db.Text)

    certificates = db.relationship(
        "Certificate",
        back_populates="worker",
        cascade="all, delete-orphan",
        order_by="Certificate.expire_date.asc()",
    )
    attendance = db.relationship(
        "TrainingAttendee", back_populates="worker", cascade="all, delete-orphan"
    )
    assignments = db.relationship(
        "TaskWorker", back_populates="worker", cascade="all, delete-orphan"
    )

    def to_brief(self):
        """下拉选项与关联展示用的精简结构。"""

        return {
            "id": self.id,
            "employee_no": self.employee_no,
            "name": self.name,
            "team": self.team,
        }

    def to_dict(self, detail=False):
        valid_cert_count = sum(1 for item in self.certificates if item.is_valid)
        expiring_count = sum(1 for item in self.certificates if item.status == "expiring")
        data = {
            "id": self.id,
            "employee_no": self.employee_no,
            "name": self.name,
            "gender": self.gender,
            "phone": self.phone,
            "team": self.team,
            "position": self.position,
            "status": self.status,
            "status_label": WORKER_STATUS.label(self.status),
            "hired_date": format_date(self.hired_date),
            "certificate_count": len(self.certificates),
            "valid_certificate_count": valid_cert_count,
            "expiring_certificate_count": expiring_count,
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
            data["certificates"] = [item.to_dict() for item in self.certificates]
        return data
