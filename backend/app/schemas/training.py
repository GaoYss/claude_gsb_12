"""培训场次校验规则。"""

from ..constants import ATTENDANCE_STATUS, TRAINING_CATEGORY, TRAINING_RESULT
from .common import PayloadValidator


def _validate_attendee(raw_item, index):
    return (
        PayloadValidator(raw_item)
        .integer("worker_id", "参加人员", required=True, min_value=1)
        .enum("attendance", "出勤情况", group=ATTENDANCE_STATUS, default="attended")
        .enum("result", "考核结果", group=TRAINING_RESULT, default="exempt")
        .number("score", "考核成绩", min_value=0, max_value=100)
        .done()
    )


def validate_training_session(payload):
    return (
        PayloadValidator(payload)
        .string("session_no", "培训编号", max_length=32)
        .string("topic", "培训主题", required=True, max_length=128)
        .enum("category", "培训类别", group=TRAINING_CATEGORY, required=True)
        .date("train_date", "培训日期", required=True)
        .number("duration_hours", "培训时长（小时）", min_value=0.5, max_value=240, digits=1)
        .string("location", "培训地点", max_length=128)
        .string("trainer", "讲师", required=True, max_length=64)
        .string("organization", "组织单位", max_length=128)
        .text("content", "培训内容", max_length=4000)
        .text("remark", "备注", max_length=2000)
        .array("attendees", "参加人员", each=_validate_attendee, max_items=200)
        .done()
    )
