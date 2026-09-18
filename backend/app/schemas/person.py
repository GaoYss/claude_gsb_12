"""人员档案校验规则。"""

from ..constants import PERSON_STATUS
from .common import PHONE_PATTERN, PayloadValidator


def validate_person(payload):
    return (
        PayloadValidator(payload)
        .string("employee_no", "工号", required=True, max_length=32)
        .string("name", "姓名", required=True, max_length=64)
        .string("team", "所属班组", max_length=64)
        .string("position", "岗位", max_length=64)
        .string("phone", "联系电话", max_length=32, pattern=PHONE_PATTERN,
                pattern_message="联系电话格式不正确")
        .enum("status", "人员状态", group=PERSON_STATUS, default="active")
        .date("entry_date", "入职日期")
        .text("remark", "备注", max_length=2000)
        .done()
    )
