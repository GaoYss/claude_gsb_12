"""特种作业证书校验规则。"""

from ..constants import CERTIFICATE_TYPE
from .common import PayloadValidator


def validate_certificate(payload):
    return (
        PayloadValidator(payload)
        .string("cert_no", "证书编号", required=True, max_length=64)
        .integer("worker_id", "持证人", required=True, min_value=1)
        .enum("cert_type", "证书类型", group=CERTIFICATE_TYPE, required=True)
        .string("issuing_authority", "发证机关", max_length=128)
        .date("issue_date", "发证日期", required=True)
        .date("expire_date", "有效期至", required=True)
        .text("remark", "备注", max_length=2000)
        .done()
    )
