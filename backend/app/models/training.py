"""培训记录模型。"""

from ..constants import ATTENDANCE_STATUS, TRAINING_CATEGORY
from ..extensions import db
from ..utils.dates import format_date, format_datetime
from ..utils.numbers import to_float
from .mixins import TimestampMixin, quantity_column


class TrainingRecord(TimestampMixin, db.Model):
    """人员培训记录：一次培训的主题、时间、讲师与参加人员。"""

    __tablename__ = "training_record"

    id = db.Column(db.Integer, primary_key=True)
    training_no = db.Column(db.String(32), nullable=False, unique=True, index=True)
    topic = db.Column(db.String(128), nullable=False, index=True)
    category = db.Column(db.String(32), nullable=False, default="safety", index=True)
    train_date = db.Column(db.Date, nullable=False, index=True)
    location = db.Column(db.String(128))
    trainer = db.Column(db.String(64), nullable=False)
    duration_hours = db.Column(quantity_column())
    content = db.Column(db.Text)
    remark = db.Column(db.Text)

    attendees = db.relationship(
        "TrainingAttendee",
        back_populates="training",
        cascade="all, delete-orphan",
        order_by="TrainingAttendee.id",
    )

    def to_dict(self, detail=False):
        attendee_items = [item.to_dict() for item in self.attendees]
        present = sum(1 for item in self.attendees if item.attendance == "present")
        data = {
            "id": self.id,
            "training_no": self.training_no,
            "topic": self.topic,
            "category": self.category,
            "category_label": TRAINING_CATEGORY.label(self.category),
            "train_date": format_date(self.train_date),
            "location": self.location,
            "trainer": self.trainer,
            "duration_hours": to_float(self.duration_hours),
            "created_at": format_datetime(self.created_at),
            "updated_at": format_datetime(self.updated_at),
            "attendee_count": len(attendee_items),
            "present_count": present,
            "attendees": attendee_items,
        }
        if detail:
            data["content"] = self.content
            data["remark"] = self.remark
        return data


class TrainingAttendee(db.Model):
    """培训参加人员：培训记录与人员的关联，附出席情况。"""

    __tablename__ = "training_attendee"
    __table_args__ = (
        db.UniqueConstraint("training_id", "person_id", name="uq_training_person"),
    )

    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(
        db.Integer,
        db.ForeignKey("training_record.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    person_id = db.Column(
        db.Integer,
        db.ForeignKey("person.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attendance = db.Column(db.String(16), nullable=False, default="present")
    score = db.Column(db.String(32))

    training = db.relationship("TrainingRecord", back_populates="attendees")
    person = db.relationship("Person", back_populates="attendance")

    def to_dict(self):
        return {
            "id": self.id,
            "person_id": self.person_id,
            "person": self.person.to_brief() if self.person else None,
            "attendance": self.attendance,
            "attendance_label": ATTENDANCE_STATUS.label(self.attendance),
            "score": self.score,
        }
