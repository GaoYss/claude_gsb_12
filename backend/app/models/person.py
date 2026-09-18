"""人员档案模型。"""

from ..constants import PERSON_STATUS
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from .mixins import TimestampMixin


class Person(TimestampMixin, db.Model):
    """养护作业人员：培训记录与持证情况的归属主体。"""

    __tablename__ = "person"

    id = db.Column(db.Integer, primary_key=True)
    employee_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    name = db.Column(db.String(64), nullable=False, index=True)
    team = db.Column(db.String(64), index=True)
    position = db.Column(db.String(64))
    phone = db.Column(db.String(32))
    status = db.Column(db.String(16), nullable=False, default="active", index=True)
    entry_date = db.Column(db.Date)
    remark = db.Column(db.Text)

    certificates = db.relationship(
        "Certificate", back_populates="person", cascade="all, delete-orphan"
    )
    attendance = db.relationship(
        "TrainingAttendee", back_populates="person", cascade="all, delete-orphan"
    )

    def to_brief(self):
        """下拉框与关联展示用的精简结构。"""

        return {
            "id": self.id,
            "employee_no": self.employee_no,
            "name": self.name,
            "team": self.team,
            "position": self.position,
            "status": self.status,
        }

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "employee_no": self.employee_no,
            "name": self.name,
            "team": self.team,
            "position": self.position,
            "phone": self.phone,
            "status": self.status,
            "status_label": PERSON_STATUS.label(self.status),
            "entry_date": format_date(self.entry_date),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["remark"] = self.remark
        return data
