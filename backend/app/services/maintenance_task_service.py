"""养护任务业务逻辑。"""

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from ..constants import CERT_TYPE, ENUM_GROUPS
from ..errors import ConflictError, ValidationError
from ..extensions import db
from ..models import (
    Certificate,
    GreenSpace,
    MaintenanceRecord,
    MaintenanceTask,
    Person,
    PlantReplacement,
    TaskAssignee,
)
from ..models.maintenance_task import OPEN_STATUSES
from ..models.mixins import utcnow
from ..utils.dates import format_date, today
from ..utils.numbers import to_float
from ..utils.sorting import parse_sort
from .base_service import BaseService
from .code_generator import daily_prefix


class MaintenanceTaskService(BaseService):
    """养护任务登记：创建、检索、状态流转、持证校验与删除保护。"""

    model = MaintenanceTask
    label = "养护任务"
    code_field = "task_no"
    code_width = 3
    transient_fields = ("assignee_ids",)

    SORTABLE = {
        "plan_date": MaintenanceTask.plan_date,
        "task_no": MaintenanceTask.task_no,
        "created_at": MaintenanceTask.created_at,
    }

    @classmethod
    def code_prefix(cls):
        return daily_prefix("MT")

    # ------------------------------------------------------------ 校验
    @classmethod
    def _resolve_assignees(cls, person_ids):
        """校验作业人员均存在且可派工，返回 Person 列表（保持传入顺序）。"""

        if not person_ids:
            return []
        people = db.session.query(Person).filter(Person.id.in_(person_ids)).all()
        people_map = {person.id: person for person in people}
        missing = [pid for pid in person_ids if pid not in people_map]
        if missing:
            raise ValidationError(
                "登记失败", details={"assignee_ids": f"{len(missing)} 名作业人员不存在，请刷新后重试"}
            )
        unavailable = [
            people_map[pid].name for pid in person_ids
            if people_map[pid].status in {"resigned"}
        ]
        if unavailable:
            raise ConflictError(f"作业人员 {('、'.join(unavailable))} 已离岗，不能再安排作业任务")
        return [people_map[pid] for pid in person_ids]

    @classmethod
    def _check_certificates(cls, cert_type, plan_date, people):
        """安排需要持证的任务时逐人校验证书在作业日当天有效。

        - 未设置持证要求：不校验；
        - 已设置要求但没有作业人员：提示先指定人员；
        - 逐人检查是否持有对应类型且在计划作业日有效的证书。
        """

        if not cert_type:
            return
        if not people:
            raise ConflictError(
                f"该任务要求「{CERT_TYPE.label(cert_type)}」持证上岗，"
                "请先指定持有效证书的作业人员"
            )
        violations = []
        for person in people:
            cert = (
                db.session.query(Certificate)
                .filter(
                    Certificate.person_id == person.id,
                    Certificate.cert_type == cert_type,
                )
                .order_by(Certificate.expire_date.desc())
                .first()
            )
            if cert is None:
                violations.append(f"人员「{person.name}」未持有{CERT_TYPE.label(cert_type)}")
            elif not cert.is_valid_on(plan_date):
                cert_label = CERT_TYPE.label(cert_type)
                if cert.status == "revoked":
                    violations.append(f"人员「{person.name}」的{cert_label}已注销，不能上岗")
                elif cert.expire_date and plan_date > cert.expire_date:
                    violations.append(
                        f"人员「{person.name}」的{cert_label}有效期至 {cert.expire_date}，"
                        f"早于作业日 {plan_date}"
                    )
                elif cert.review_date and plan_date > cert.review_date:
                    violations.append(
                        f"人员「{person.name}」的{cert_label}复审日期为 {cert.review_date}，"
                        f"作业日 {plan_date} 前须完成复审"
                    )
                else:
                    violations.append(f"人员「{person.name}」的{cert_label}在作业日 {plan_date} 无效")
        if violations:
            raise ConflictError("持证上岗校验未通过：" + "；".join(violations))

    @classmethod
    def prepare_instance(cls, instance, payload):
        green_space_id = payload.get("green_space_id", instance.green_space_id)
        space = db.session.get(GreenSpace, green_space_id) if green_space_id else None
        if space is None:
            raise ValidationError("登记失败", details={"green_space_id": "所选绿地不存在"})
        if space.status == "archived":
            raise ConflictError(f"绿地「{space.name}」已归档，不能再登记养护任务")

        # 持证校验需使用本次提交的最终值（update 时实例字段还是旧值）
        assignee_ids = getattr(instance, "_pending_assignee_ids", None)
        if assignee_ids is not None:
            people = cls._resolve_assignees(assignee_ids)
        elif instance.id is not None:
            # 更新时未重交人员名单：沿用现有作业人员
            people = [link.person for link in instance.assignees if link.person]
        else:
            return
        cert_type = payload.get("required_cert_type", instance.required_cert_type)
        plan_date = payload.get("plan_date", instance.plan_date)
        cls._check_certificates(cert_type, plan_date, people)

    @classmethod
    def after_create(cls, instance, payload):
        cls._sync_assignees(instance, getattr(instance, "_pending_assignee_ids", None))

    @classmethod
    def after_update(cls, instance, payload):
        cls._sync_assignees(instance, getattr(instance, "_pending_assignee_ids", None))

    @classmethod
    def _sync_assignees(cls, task, person_ids):
        """按提交的人员列表重建任务作业人员关联。"""

        if person_ids is None:
            return
        db.session.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).delete(
            synchronize_session=False
        )
        for person_id in person_ids:
            db.session.add(TaskAssignee(task_id=task.id, person_id=person_id))
        db.session.flush()
        db.session.expire(task, ["assignees"])

    @classmethod
    def apply_derived(cls, instance):
        """状态与完成时间保持一致：完成即写入完成时间，撤销完成即清空。"""

        if instance.status == "completed":
            if instance.completed_at is None:
                instance.completed_at = utcnow()
        else:
            instance.completed_at = None

    @classmethod
    def _apply_filters(cls, query, filters):
        if filters.get("green_space_id"):
            query = query.filter(MaintenanceTask.green_space_id == filters["green_space_id"])
        if filters.get("status"):
            query = query.filter(MaintenanceTask.status == filters["status"])
        if filters.get("task_type"):
            query = query.filter(MaintenanceTask.task_type == filters["task_type"])
        if filters.get("priority"):
            query = query.filter(MaintenanceTask.priority == filters["priority"])
        if filters.get("date_from"):
            query = query.filter(MaintenanceTask.plan_date >= filters["date_from"])
        if filters.get("date_to"):
            query = query.filter(MaintenanceTask.plan_date <= filters["date_to"])
        if filters.get("overdue"):
            query = query.filter(
                MaintenanceTask.status.in_(OPEN_STATUSES),
                MaintenanceTask.plan_date < today(),
            )
        if filters.get("unplanned"):
            query = query.filter(MaintenanceTask.status == "pending")
        if filters.get("cert_required"):
            query = query.filter(MaintenanceTask.required_cert_type.isnot(None))
        if filters.get("required_cert_type"):
            query = query.filter(
                MaintenanceTask.required_cert_type == filters["required_cert_type"]
            )
        keyword = filters.get("keyword")
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    MaintenanceTask.task_no.like(like),
                    MaintenanceTask.title.like(like),
                    MaintenanceTask.executor.like(like),
                    MaintenanceTask.description.like(like),
                )
            )
        return query

    # ------------------------------------------------------------ 查询
    @classmethod
    def list_tasks(cls, filters, args):
        """列表查询：附带每条任务的养护记录进度，便于一眼看出执行情况。"""

        record_count = (
            db.select(func.count(MaintenanceRecord.id))
            .where(MaintenanceRecord.task_id == MaintenanceTask.id)
            .correlate(MaintenanceTask)
            .scalar_subquery()
        )
        qualified_count = (
            db.select(func.count(MaintenanceRecord.id))
            .where(
                MaintenanceRecord.task_id == MaintenanceTask.id,
                MaintenanceRecord.quality_result == "qualified",
            )
            .correlate(MaintenanceTask)
            .scalar_subquery()
        )
        query = db.session.query(
            MaintenanceTask,
            record_count.label("record_count"),
            qualified_count.label("qualified_count"),
        ).options(
            joinedload(MaintenanceTask.assignees).joinedload(TaskAssignee.person)
        )
        query = cls._apply_filters(query, filters)
        query = query.order_by(parse_sort(args, cls.SORTABLE, MaintenanceTask.plan_date.desc()))
        return query

    @classmethod
    def serialize_row(cls, row):
        task, record_count, qualified_count = row
        data = task.to_dict()
        data["progress"] = {
            "record_count": record_count or 0,
            "qualified_count": qualified_count or 0,
        }
        return data

    @classmethod
    def detail(cls, obj_id):
        task = cls.get(obj_id)
        records = (
            db.session.query(MaintenanceRecord)
            .filter(MaintenanceRecord.task_id == task.id)
            .order_by(MaintenanceRecord.record_date.desc(), MaintenanceRecord.id.desc())
            .all()
        )
        replacement_stats = db.session.query(
            func.count(PlantReplacement.id),
            func.coalesce(func.sum(PlantReplacement.quantity), 0),
            func.coalesce(func.sum(PlantReplacement.amount), 0),
        ).join(MaintenanceRecord, PlantReplacement.maintenance_record_id == MaintenanceRecord.id) \
            .filter(MaintenanceRecord.task_id == task.id).one()

        data = task.to_dict(detail=True)
        data["records"] = [item.to_dict() for item in records]
        data["progress"] = {
            "record_count": len(records),
            "qualified_count": sum(1 for item in records if item.quality_result == "qualified"),
            "unqualified_count": sum(1 for item in records if item.quality_result == "unqualified"),
            "total_work_hours": to_float(sum((item.work_hours or 0) for item in records)) or 0,
            "replacement_count": replacement_stats[0] or 0,
            "replacement_quantity": to_float(replacement_stats[1]) or 0,
            "replacement_amount": to_float(replacement_stats[2]) or 0,
            "last_record_date": format_date(records[0].record_date) if records else None,
        }
        return data

    # ------------------------------------------------------------ 状态流转
    @classmethod
    def change_status(cls, obj_id, payload):
        """手动流转任务状态。

        规则：存在不合格养护记录时不允许直接标记完成，需先整改；
        标记完成会写入完成时间，撤销完成则清空完成时间。
        """

        task = cls.get(obj_id)
        status = payload["status"]
        if payload.get("description") is not None:
            task.description = payload["description"]

        # 开工即意味着人员实际进场作业，此时复核持证情况（按计划作业日校验）
        if status == "in_progress" and task.status != "in_progress":
            people = [link.person for link in task.assignees if link.person]
            cls._check_certificates(task.required_cert_type, task.plan_date, people)

        if status == "completed":
            unqualified = (
                db.session.query(func.count(MaintenanceRecord.id))
                .filter(
                    MaintenanceRecord.task_id == task.id,
                    MaintenanceRecord.quality_result == "unqualified",
                )
                .scalar()
                or 0
            )
            if unqualified:
                raise ConflictError(
                    f"该任务存在 {unqualified} 条不合格养护记录，请整改复检合格后再标记完成"
                )
            task.completed_at = task.completed_at or utcnow()
        else:
            task.completed_at = None

        task.status = status
        db.session.commit()
        return task

    # ------------------------------------------------------------ 删除
    @classmethod
    def delete(cls, obj_id, force=False):
        task = cls.get(obj_id)
        record_count = (
            db.session.query(func.count(MaintenanceRecord.id))
            .filter(MaintenanceRecord.task_id == task.id)
            .scalar()
            or 0
        )
        if record_count and not force:
            raise ConflictError(
                f"该任务已登记 {record_count} 条养护记录，请确认后再删除",
                details={"maintenance_record": record_count},
            )
        if record_count:
            # 强制删除时保留养护记录，仅解除任务关联，避免历史数据丢失
            db.session.query(MaintenanceRecord).filter(
                MaintenanceRecord.task_id == task.id
            ).update({MaintenanceRecord.task_id: None}, synchronize_session=False)
        db.session.delete(task)
        db.session.commit()
        return {"detached_records": record_count}

    @classmethod
    def status_summary(cls):
        rows = (
            db.session.query(MaintenanceTask.status, func.count(MaintenanceTask.id))
            .group_by(MaintenanceTask.status)
            .all()
        )
        summary = {code: 0 for code in ENUM_GROUPS["task_status"].values}
        for status, count in rows:
            summary[status] = count
        return summary
