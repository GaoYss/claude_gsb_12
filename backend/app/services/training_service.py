"""培训场次业务逻辑。"""

from sqlalchemy import func, or_

from ..errors import ValidationError
from ..extensions import db
from ..models import TrainingAttendee, TrainingSession, Worker
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix


class TrainingSessionService(BaseService):
    """培训场次：登记主题、时间、讲师与参加人员（出勤/考核）。"""

    model = TrainingSession
    label = "培训记录"
    code_field = "session_no"
    code_width = 3
    collection_fields = ("attendees",)

    SORTABLE = {
        "train_date": TrainingSession.train_date,
        "session_no": TrainingSession.session_no,
        "created_at": TrainingSession.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("TR")

    # ------------------------------------------------------------ 写入
    @classmethod
    def prepare_instance(cls, instance, payload):
        duration = payload.get("duration_hours", instance.duration_hours)
        if duration is not None and float(duration) <= 0:
            raise ValidationError("登记失败", details={"duration_hours": "培训时长必须大于 0"})

    @classmethod
    def sync_collections(cls, instance, collections, *, creating):
        """重建参加人员明细；请求显式携带 attendees 时整体覆盖。"""

        if "attendees" not in collections:
            return
        cls._sync_attendees(instance, collections["attendees"])

    @classmethod
    def _sync_attendees(cls, session, items):
        seen = set()
        for item in items:
            worker_id = item["worker_id"]
            if worker_id in seen:
                raise ValidationError(
                    "登记失败", details={"attendees": f"参加人员重复：工号 {worker_id}"}
                )
            seen.add(worker_id)

        workers = (
            db.session.query(Worker).filter(Worker.id.in_(seen)).all() if seen else []
        )
        existing = {worker.id: worker for worker in workers}
        missing = sorted(seen - set(existing))
        if missing:
            raise ValidationError(
                "登记失败",
                details={"attendees": f"参加人员不存在：{', '.join(str(i) for i in missing)}"},
            )

        # 出勤为请假/缺席时考核结果没有意义，统一落为免考；直接走 service 时补齐默认值
        for item in items:
            attendance = item.get("attendance", "attended")
            item["attendance"] = attendance
            if attendance != "attended":
                item["result"] = "exempt"
            else:
                item.setdefault("result", "exempt")

        # 整体替换参加人员集合，旧明细由 delete-orphan 级联清理
        session.attendees = [
            TrainingAttendee(
                worker_id=item["worker_id"],
                attendance=item.get("attendance", "attended"),
                result=item.get("result", "exempt"),
                score=item.get("score"),
            )
            for item in items
        ]

    # ------------------------------------------------------------ 查询
    @staticmethod
    def _apply_filters(query, filters):
        if filters.get("category"):
            query = query.filter(TrainingSession.category == filters["category"])
        if filters.get("worker_id"):
            query = query.filter(
                TrainingSession.attendees.any(TrainingAttendee.worker_id == filters["worker_id"])
            )
        if filters.get("date_from"):
            query = query.filter(TrainingSession.train_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(TrainingSession.train_date <= filters["date_to"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    TrainingSession.session_no.like(like),
                    TrainingSession.topic.like(like),
                    TrainingSession.trainer.like(like),
                    TrainingSession.location.like(like),
                    TrainingSession.organization.like(like),
                )
            )
        return query

    @classmethod
    def list_sessions(cls, filters, args):
        query = cls._apply_filters(db.session.query(TrainingSession), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, TrainingSession.train_date.desc())
        )

    @classmethod
    def detail(cls, obj_id):
        return cls.get(obj_id).to_dict(detail=True)

    @classmethod
    def summary(cls, filters):
        """培训汇总：场次、人次与出勤/合格统计。"""

        query = cls._apply_filters(db.session.query(TrainingSession), filters)
        session_ids = [row[0] for row in query.with_entities(TrainingSession.id).all()]
        total = len(session_ids)
        if not session_ids:
            return {
                "session_count": 0,
                "attendee_count": 0,
                "attended_count": 0,
                "qualified_count": 0,
                "total_hours": 0,
            }
        attendee_total, attended_total, qualified_total = db.session.query(
            func.count(TrainingAttendee.id),
            func.coalesce(func.sum(
                db.case((TrainingAttendee.attendance == "attended", 1), else_=0)
            ), 0),
            func.coalesce(func.sum(
                db.case((TrainingAttendee.result == "qualified", 1), else_=0)
            ), 0),
        ).filter(TrainingAttendee.session_id.in_(session_ids)).one()
        total_hours = (
            query.with_entities(func.coalesce(func.sum(TrainingSession.duration_hours), 0))
            .scalar()
        )
        return {
            "session_count": total,
            "attendee_count": attendee_total or 0,
            "attended_count": attended_total or 0,
            "qualified_count": qualified_total or 0,
            "total_hours": float(total_hours or 0),
        }
