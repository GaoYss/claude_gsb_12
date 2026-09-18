"""人员培训记录业务逻辑。"""

from sqlalchemy import exists, func, or_

from ..constants import TRAINING_CATEGORY
from ..errors import ValidationError
from ..extensions import db
from ..models import Person, TrainingAttendee, TrainingRecord
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix


class TrainingRecordService(BaseService):
    """培训登记：主题、时间、讲师、参加人员及出席情况。"""

    model = TrainingRecord
    label = "培训记录"
    code_field = "training_no"
    code_width = 3
    transient_fields = ("attendees",)

    SORTABLE = {
        "train_date": TrainingRecord.train_date,
        "training_no": TrainingRecord.training_no,
        "created_at": TrainingRecord.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("TR")

    # ------------------------------------------------------------ 校验
    @classmethod
    def _sync_attendees(cls, training, attendees):
        """按提交的人员列表重建关联（含出席情况）。"""

        if attendees is None:
            return
        person_ids = [item["person_id"] for item in attendees]
        people = []
        if person_ids:
            people = db.session.query(Person).filter(Person.id.in_(person_ids)).all()
            found = {person.id for person in people}
            missing = [pid for pid in person_ids if pid not in found]
            if missing:
                raise ValidationError(
                    "登记失败", details={"attendees": f"{len(missing)} 名参加人员不存在，请刷新后重试"}
                )

        # 全量替换：先清空再按提交顺序写入
        db.session.query(TrainingAttendee).filter(
            TrainingAttendee.training_id == training.id
        ).delete(synchronize_session=False)
        for item in attendees:
            db.session.add(TrainingAttendee(
                training_id=training.id,
                person_id=item["person_id"],
                attendance=item.get("attendance", "present"),
                score=item.get("score"),
            ))
        db.session.flush()
        db.session.expire(training, ["attendees"])

    @classmethod
    def after_create(cls, instance, payload):
        cls._sync_attendees(instance, getattr(instance, "_pending_attendees", None))

    @classmethod
    def after_update(cls, instance, payload):
        cls._sync_attendees(instance, getattr(instance, "_pending_attendees", None))

    # ------------------------------------------------------------ 查询
    @staticmethod
    def _apply_filters(query, filters):
        if filters.get("category"):
            query = query.filter(TrainingRecord.category == filters["category"])
        if filters.get("trainer"):
            query = query.filter(TrainingRecord.trainer.like(f"%{filters['trainer']}%"))
        if filters.get("date_from"):
            query = query.filter(TrainingRecord.train_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(TrainingRecord.train_date <= filters["date_to"])
        if filters.get("person_id"):
            query = query.filter(
                exists().where(
                    TrainingAttendee.training_id == TrainingRecord.id,
                    TrainingAttendee.person_id == filters["person_id"],
                )
            )
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    TrainingRecord.training_no.like(like),
                    TrainingRecord.topic.like(like),
                    TrainingRecord.trainer.like(like),
                    TrainingRecord.location.like(like),
                    TrainingRecord.content.like(like),
                )
            )
        return query

    @classmethod
    def list_trainings(cls, filters, args):
        """列表查询：子查询带出参加人数与出席人数，避免 N+1。"""

        attendee_count = (
            db.select(func.count(TrainingAttendee.id))
            .where(TrainingAttendee.training_id == TrainingRecord.id)
            .correlate(TrainingRecord)
            .scalar_subquery()
        )
        present_count = (
            db.select(func.count(TrainingAttendee.id))
            .where(
                TrainingAttendee.training_id == TrainingRecord.id,
                TrainingAttendee.attendance == "present",
            )
            .correlate(TrainingRecord)
            .scalar_subquery()
        )
        query = db.session.query(
            TrainingRecord, attendee_count.label("attendee_count"),
            present_count.label("present_count"),
        )
        query = cls._apply_filters(query, filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, TrainingRecord.train_date.desc())
        )

    @classmethod
    def serialize_row(cls, row):
        """列表精简结构：只带参加人数，不嵌套人员明细。"""

        item, attendee_count, present_count = row
        return {
            "id": item.id,
            "training_no": item.training_no,
            "topic": item.topic,
            "category": item.category,
            "category_label": TRAINING_CATEGORY.label(item.category),
            "train_date": item.train_date.isoformat(),
            "location": item.location,
            "trainer": item.trainer,
            "duration_hours": item.duration_hours if item.duration_hours is None else float(item.duration_hours),
            "attendee_count": attendee_count or 0,
            "present_count": present_count or 0,
        }

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def category_summary(cls):
        rows = (
            db.session.query(TrainingRecord.category, func.count(TrainingRecord.id))
            .group_by(TrainingRecord.category)
            .all()
        )
        return [{"category": category, "count": count} for category, count in rows]
