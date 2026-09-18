"""作业人员业务逻辑。"""

from sqlalchemy import func, or_

from ..constants import TRAINING_CATEGORY
from ..errors import ConflictError
from ..extensions import db
from ..models import Certificate, TaskWorker, TrainingAttendee, Worker
from ..utils.sorting import parse_sort
from .base_service import BaseService


class WorkerService(BaseService):
    """作业人员档案：建档、检索、下拉选项与删除保护。"""

    model = Worker
    label = "作业人员"
    code_field = "employee_no"
    code_width = 4

    SORTABLE = {
        "employee_no": Worker.employee_no,
        "name": Worker.name,
        "hired_date": Worker.hired_date,
        "created_at": Worker.created_at,
    }

    @classmethod
    def code_prefix(cls):
        """工号按年递增，如 WK-2026-0001。"""

        from .code_generator import year_prefix

        return year_prefix("WK")

    # ------------------------------------------------------------ 查询
    @staticmethod
    def _apply_filters(query, filters):
        if filters.get("status"):
            query = query.filter(Worker.status == filters["status"])
        if filters.get("team"):
            query = query.filter(Worker.team == filters["team"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Worker.employee_no.like(like),
                    Worker.name.like(like),
                    Worker.phone.like(like),
                    Worker.team.like(like),
                    Worker.position.like(like),
                )
            )
        return query

    @classmethod
    def list_workers(cls, filters, args):
        query = cls._apply_filters(db.session.query(Worker), filters)
        return query.order_by(
            parse_sort(args, cls.SORTABLE, Worker.employee_no.asc())
        )

    @classmethod
    def options(cls, keyword=None, cert_type=None, limit=100):
        """下拉选项：默认仅在岗人员；cert_type 时只返回持有该类有效证书的人员。"""

        query = db.session.query(Worker).filter(Worker.status == "active")
        if cert_type:
            query = query.join(Certificate, Certificate.worker_id == Worker.id).filter(
                Certificate.cert_type == cert_type,
                Certificate.expire_date >= func.current_date(),
            )
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(Worker.name.like(like), Worker.employee_no.like(like)))
        query = query.order_by(Worker.employee_no.asc()).limit(limit)
        return [item.to_brief() for item in query.all()]

    @classmethod
    def teams(cls):
        rows = (
            db.session.query(Worker.team, func.count(Worker.id))
            .filter(Worker.team.isnot(None))
            .group_by(Worker.team)
            .order_by(Worker.team.asc())
            .all()
        )
        return [{"team": team, "count": count} for team, count in rows]

    @classmethod
    def detail(cls, obj_id):
        """人员档案：基本信息 + 证书 + 近期培训 + 派工任务。"""

        worker = cls.get(obj_id)
        records = (
            db.session.query(TrainingAttendee)
            .filter(TrainingAttendee.worker_id == worker.id)
            .order_by(TrainingAttendee.id.desc())
            .limit(10)
            .all()
        )
        assignments = (
            db.session.query(TaskWorker)
            .filter(TaskWorker.worker_id == worker.id)
            .order_by(TaskWorker.id.desc())
            .limit(10)
            .all()
        )
        data = worker.to_dict(detail=True)
        data["training_records"] = [
            {
                **item.to_dict(),
                "session_no": item.session.session_no if item.session else None,
                "topic": item.session.topic if item.session else None,
                "category": item.session.category if item.session else None,
                "category_label": (
                    TRAINING_CATEGORY.label(item.session.category) if item.session else None
                ),
                "train_date": item.session.train_date.isoformat() if item.session else None,
            }
            for item in records
        ]
        data["task_assignments"] = [
            {
                "task_id": item.task_id,
                "task_no": item.task.task_no if item.task else None,
                "title": item.task.title if item.task else None,
                "plan_date": item.task.plan_date.isoformat() if item.task else None,
                "status": item.task.status if item.task else None,
                "required_cert_type": item.task.required_cert_type if item.task else None,
            }
            for item in assignments
        ]
        return data

    # ------------------------------------------------------------ 写入
    @classmethod
    def delete(cls, obj_id, force=False):
        worker = cls.get(obj_id)
        counts = {
            "certificate": db.session.query(func.count(Certificate.id))
            .filter(Certificate.worker_id == worker.id)
            .scalar()
            or 0,
            "training_attendee": db.session.query(func.count(TrainingAttendee.id))
            .filter(TrainingAttendee.worker_id == worker.id)
            .scalar()
            or 0,
            "task_worker": db.session.query(func.count(TaskWorker.id))
            .filter(TaskWorker.worker_id == worker.id)
            .scalar()
            or 0,
        }
        if sum(counts.values()) and not force:
            raise ConflictError(
                "该人员已有证书 {certificate} 条、培训记录 {training_attendee} 条、"
                "任务派工 {task_worker} 条，删除将一并清除，请确认后重试".format(**counts),
                details=counts,
            )
        db.session.delete(worker)
        db.session.commit()
        return counts
