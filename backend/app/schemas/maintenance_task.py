"""养护任务校验规则。"""

from ..constants import CERTIFICATE_TYPE, TASK_PRIORITY, TASK_STATUS, TASK_TYPE
from .common import PayloadValidator, ValidationError


def _validate_worker_id(raw_item, index):
    if isinstance(raw_item, bool) or not isinstance(raw_item, int) or raw_item < 1:
        raise ValidationError("提交的数据未通过校验", details={"worker_id": "作业人员必须是有效编号"})
    return raw_item


def validate_maintenance_task(payload):
    return (
        PayloadValidator(payload)
        .string("task_no", "任务编号", max_length=32)
        .integer("green_space_id", "所属绿地", required=True, min_value=1)
        .string("title", "任务名称", required=True, max_length=128)
        .enum("task_type", "养护类型", group=TASK_TYPE, required=True)
        .date("plan_date", "计划养护日期", required=True)
        .enum("priority", "优先级", group=TASK_PRIORITY, default="medium")
        .string("executor", "执行班组/负责人", max_length=64)
        .enum("required_cert_type", "持证要求", group=CERTIFICATE_TYPE)
        .array("worker_ids", "作业人员", each=_validate_worker_id, max_items=100)
        .enum("status", "任务状态", group=TASK_STATUS, default="pending")
        .text("description", "任务说明", max_length=2000)
        .done()
    )


def validate_task_status(payload):
    """任务状态流转：只允许变更状态与说明。"""

    return (
        PayloadValidator(payload)
        .enum("status", "任务状态", group=TASK_STATUS, required=True)
        .text("description", "任务说明", max_length=2000)
        .done()
    )
