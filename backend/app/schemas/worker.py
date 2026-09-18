"""作业人员校验规则。"""

from ..constants import WORKER_STATUS
from .common import PHONE_PATTERN, PayloadValidator


def validate_worker(payload):
    return (
        PayloadValidator(payload)
        .string("employee_no", "工号", max_length=32)
        .string("name", "姓名", required=True, max_length=64)
        .string("gender", "性别", max_length=8)
        .string("phone", "联系电话", max_length=24,
                 pattern=PHONE_PATTERN, pattern_message="联系电话格式不正确")
        .string("team", "所属班组", max_length=64)
        .string("position", "岗位", max_length=64)
        .enum("status", "在岗状态", group=WORKER_STATUS, default="active")
        .date("hired_date", "入职日期")
        .text("remark", "备注", max_length=2000)
        .done()
    )
