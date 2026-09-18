"""人员培训记录模型：培训场次与参加人员明细。"""

from ..constants import ATTENDANCE_STATUS, TRAINING_CATEGORY, TRAINING_RESULT
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from .mixins import TimestampMixin, utcnow


class TrainingSession(TimestampMixin, db.Model):
    """培训场次：记录培训主题、时间、地点、讲师与参加人员。"""

    __tablename__ = "training_session"

    id = db.Column(db.Integer, primary_key=True)
    session_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    topic = db.Column(db.String(128), nullable=False, index=True)
    category = db.Column(db.String(32), nullable=False, index=True)
    train_date = db.Column(db.Date, nullable=False, index=True)
    duration_hours = db.Column(db.Numeric(6, 1, asdecimal=False))
    location = db.Column(db.String(128))
    trainer = db.Column(db.String(64), nullable=False)
    organization = db.Column(db.String(128))
    content = db.Column(db.Text)
    remark = db.Column(db.Text)

    attendees = db.relationship(
        "TrainingAttendee",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TrainingAttendee.id.asc()",
    )

    def to_dict(self, detail=False):
        attended = [item for item in self.attendees if item.attendance == "attended"]
        data = {
            "id": self.id,
            "session_no": self.session_no,
            "topic": self.topic,
            "category": self.category,
            "category_label": TRAINING_CATEGORY.label(self.category),
            "train_date": format_date(self.train_date),
            "duration_hours": self.duration_hours,
            "location": self.location,
            "trainer": self.trainer,
            "organization": self.organization,
            "attendee_count": len(self.attendees),
            "attended_count": len(attended),
            "qualified_count": sum(1 for item in attended if item.result == "qualified"),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
        }
        if detail:
            data["content"] = self.content
            data["remark"] = self.remark
            data["attendees"] = [item.to_dict() for item in self.attendees]
        return data


class TrainingAttendee(db.Model):
    """培训参加人员明细：出勤情况与考核结果。"""

    __tablename__ = "training_attendee"
    __table_args__ = (
        db.UniqueConstraint("session_id", "worker_id", name="uq_training_attendee"),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("training_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_id = db.Column(
        db.Integer, db.ForeignKey("worker.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attendance = db.Column(db.String(16), nullable=False, default="attended")
    result = db.Column(db.String(16), default="exempt")
    score = db.Column(db.Numeric(6, 2, asdecimal=False))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    session = db.relationship("TrainingSession", back_populates="attendees")
    worker = db.relationship("Worker", back_populates="attendance", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "worker_id": self.worker_id,
            "worker": self.worker.to_brief() if self.worker else None,
            "attendance": self.attendance,
            "attendance_label": ATTENDANCE_STATUS.label(self.attendance),
            "result": self.result,
            "result_label": TRAINING_RESULT.label(self.result) if self.result else None,
            "score": self.score,
        }
