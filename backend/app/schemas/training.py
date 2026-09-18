"""培训记录校验规则。"""

from ..constants import ATTENDANCE_STATUS, TRAINING_CATEGORY
from ..errors import ValidationError
from .common import PayloadValidator


def _validate_attendees(raw):
    """校验参加人员列表：[{person_id, attendance, score}]，按人员去重。

    返回 None 表示请求未提供该字段（更新时保留原名单）；
    返回列表（含空列表）表示按提交内容全量替换。
    """

    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValidationError("提交的数据未通过校验", details={"attendees": "参加人员必须是数组"})
    if len(raw) > 200:
        raise ValidationError("提交的数据未通过校验", details={"attendees": "参加人员最多 200 人"})

    attendees = []
    seen = set()
    for index, item in enumerate(raw):
        field = f"attendees[{index}]"
        if not isinstance(item, dict):
            raise ValidationError("提交的数据未通过校验", details={field: "参加人员格式不正确"})
        person_id = item.get("person_id")
        try:
            person_id = int(str(person_id).strip())
        except (TypeError, ValueError, AttributeError):
            raise ValidationError("提交的数据未通过校验",
                                  details={f"attendees[{index}].person_id": "请选择参加人员"})
        if person_id < 1:
            raise ValidationError("提交的数据未通过校验",
                                  details={f"attendees[{index}].person_id": "人员编号不合法"})
        if person_id in seen:
            # 同一人员重复出现时忽略后一条，避免唯一约束冲突
            continue
        seen.add(person_id)

        attendance = str(item.get("attendance") or "present").strip()
        if not ATTENDANCE_STATUS.has(attendance):
            raise ValidationError(
                "提交的数据未通过校验",
                details={f"attendees[{index}].attendance": "出席情况取值不合法"},
            )
        score = item.get("score")
        if score is not None and str(score).strip():
            score = str(score).strip()[:32]
        else:
            score = None
        attendees.append({"person_id": person_id, "attendance": attendance, "score": score})
    return attendees


def validate_training(payload):
    data = (
        PayloadValidator(payload)
        .string("training_no", "培训编号", max_length=32)
        .string("topic", "培训主题", required=True, max_length=128)
        .enum("category", "培训类别", group=TRAINING_CATEGORY, default="safety")
        .date("train_date", "培训日期", required=True)
        .string("location", "培训地点", max_length=128)
        .string("trainer", "讲师", required=True, max_length=64)
        .number("duration_hours", "培训学时", min_value=0.5, max_value=99, digits=1)
        .text("content", "培训内容", max_length=4000)
        .text("remark", "备注", max_length=2000)
        .done()
    )
    data["attendees"] = _validate_attendees(payload.get("attendees"))
    return data


def validate_training_attendees(payload):
    """单独调整参加人员（签到/补登）时的校验。"""

    return {"attendees": _validate_attendees(payload.get("attendees"))}
