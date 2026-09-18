"""特种作业证书校验规则。"""

from ..constants import CERT_TYPE, CERTIFICATE_STATUS
from ..errors import ValidationError
from .common import PayloadValidator


def validate_certificate(payload):
    data = (
        PayloadValidator(payload)
        .string("cert_no", "证书编号", required=True, max_length=64)
        .integer("person_id", "持证人", required=True, min_value=1)
        .enum("cert_type", "证书类型", group=CERT_TYPE, required=True)
        .string("issuer", "发证机关", max_length=128)
        .date("issue_date", "发证日期", required=True)
        .date("expire_date", "有效期至", required=True)
        .date("review_date", "下次复审日期")
        .enum("status", "登记状态", group=CERTIFICATE_STATUS, default="active")
        .text("remark", "备注", max_length=2000)
        .done()
    )
    issue_date = data.get("issue_date")
    expire_date = data.get("expire_date")
    review_date = data.get("review_date")
    if issue_date and expire_date and expire_date < issue_date:
        raise ValidationError(
            "提交的数据未通过校验", details={"expire_date": "有效期至不能早于发证日期"}
        )
    if review_date:
        if issue_date and review_date < issue_date:
            raise ValidationError(
                "提交的数据未通过校验", details={"review_date": "复审日期不能早于发证日期"}
            )
        if expire_date and review_date > expire_date:
            raise ValidationError(
                "提交的数据未通过校验", details={"review_date": "复审日期不能晚于有效期至"}
            )
    return data


def validate_certificate_status(payload):
    """证书登记状态流转：在册 / 已注销。"""

    return (
        PayloadValidator(payload)
        .enum("status", "登记状态", group=CERTIFICATE_STATUS, required=True)
        .done()
    )
