"""人员档案业务逻辑。"""

from sqlalchemy import func, or_

from ..constants import PERSON_STATUS
from ..errors import ConflictError
from ..extensions import db
from ..models import Certificate, Person, TaskAssignee, TrainingAttendee, TrainingRecord
from ..utils.sorting import parse_sort
from .base_service import BaseService


class PersonService(BaseService):
    """人员建档、检索与删除保护。"""

    model = Person
    label = "人员"
    code_field = "employee_no"
    code_width = 4          # 人员工号允许手工指定，不做自动生成

    SORTABLE = {
        "employee_no": Person.employee_no,
        "name": Person.name,
        "entry_date": Person.entry_date,
        "created_at": Person.created_at,
    }

    # 工号由外部（人事编号）指定，不自动生成
    @classmethod
    def generate_code(cls):
        return None

    # ------------------------------------------------------------ 查询
    @staticmethod
    def _apply_filters(query, filters):
        if filters.get("status"):
            query = query.filter(Person.status == filters["status"])
        if filters.get("team"):
            query = query.filter(Person.team == filters["team"])
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    Person.name.like(like),
                    Person.employee_no.like(like),
                    Person.team.like(like),
                    Person.position.like(like),
                )
            )
        return query

    @classmethod
    def list_people(cls, filters, args):
        """列表查询：带出持证数量与近期培训次数，便于一屏掌握人员情况。"""

        cert_count = (
            db.select(func.count(Certificate.id))
            .where(Certificate.person_id == Person.id)
            .correlate(Person)
            .scalar_subquery()
        )
        valid_cert_count = (
            db.select(func.count(Certificate.id))
            .where(
                Certificate.person_id == Person.id,
                Certificate.status == "active",
            )
            .correlate(Person)
            .scalar_subquery()
        )
        training_count = (
            db.select(func.count(TrainingAttendee.id))
            .where(TrainingAttendee.person_id == Person.id)
            .correlate(Person)
            .scalar_subquery()
        )
        query = db.session.query(
            Person,
            cert_count.label("cert_count"),
            valid_cert_count.label("active_cert_count"),
            training_count.label("training_count"),
        )
        query = cls._apply_filters(query, filters)
        query = query.order_by(parse_sort(args, cls.SORTABLE, Person.employee_no.asc()))
        return query

    @classmethod
    def serialize_row(cls, row):
        person, cert_count, active_cert_count, training_count = row
        data = person.to_dict()
        data["statistics"] = {
            "certificate_count": cert_count or 0,
            "active_certificate_count": active_cert_count or 0,
            "training_count": training_count or 0,
        }
        return data

    @classmethod
    def options(cls, keyword=None, team=None, include_inactive=False, limit=50):
        """人员下拉：默认仅返回在岗人员，筛选场景可包含离岗人员。"""

        query = db.session.query(Person)
        if not include_inactive:
            query = query.filter(Person.status == "active")
        if team:
            query = query.filter(Person.team == team)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(Person.name.like(like), Person.employee_no.like(like)))
        query = query.order_by(Person.employee_no.asc()).limit(limit)
        return [item.to_brief() for item in query.all()]

    @classmethod
    def detail(cls, obj_id):
        person = cls.get(obj_id)
        trainings = (
            db.session.query(TrainingAttendee)
            .join(TrainingRecord, TrainingAttendee.training_id == TrainingRecord.id)
            .filter(TrainingAttendee.person_id == person.id)
            .order_by(TrainingRecord.train_date.desc(), TrainingAttendee.id.desc())
            .all()
        )
        data = person.to_dict(detail=True)
        data["certificates"] = [item.to_dict() for item in person.certificates]
        data["trainings"] = [
            {
                "training_id": item.training_id,
                "training_no": item.training.training_no if item.training else None,
                "topic": item.training.topic if item.training else None,
                "category": item.training.category if item.training else None,
                "train_date": item.training.train_date.isoformat() if item.training else None,
                "trainer": item.training.trainer if item.training else None,
                "attendance": item.attendance,
                "score": item.score,
            }
            for item in trainings
        ]
        return data

    # ------------------------------------------------------------ 删除
    @classmethod
    def delete(cls, obj_id):
        person = cls.get(obj_id)
        task_count = (
            db.session.query(func.count(TaskAssignee.id))
            .filter(TaskAssignee.person_id == person.id)
            .scalar()
            or 0
        )
        if task_count:
            raise ConflictError(
                f"人员「{person.name}」已被安排到 {task_count} 个养护任务，"
                "请先调整任务作业人员后再删除；离岗人员建议将状态改为「离岗」",
                details={"maintenance_task": task_count},
            )
        db.session.delete(person)
        db.session.commit()
        return {"training_attendee": len(person.attendance)}

    @classmethod
    def status_summary(cls):
        rows = (
            db.session.query(Person.status, func.count(Person.id))
            .group_by(Person.status)
            .all()
        )
        summary = {code: 0 for code in PERSON_STATUS.values}
        for status, count in rows:
            summary[status] = count
        return summary
