"""列表查询过滤条件解析。

过滤条件从 querystring 读取，非法值直接忽略，不打断列表查询。
"""

from ..constants import ENUM_GROUPS
from ..utils.dates import parse_date


def _text(args, key):
    value = (args.get(key) or "").strip()
    return value or None


def _int(args, key):
    try:
        return int(str(args.get(key)).strip())
    except (TypeError, ValueError):
        return None


def _enum(args, key, group_key):
    value = (args.get(key) or "").strip()
    return value if value and ENUM_GROUPS[group_key].has(value) else None


def _date(args, key):
    value = (args.get(key) or "").strip()
    if not value:
        return None
    try:
        return parse_date(value, "日期")
    except ValueError:
        return None


def _flag(args, key):
    return str(args.get(key, "")).strip().lower() in {"1", "true", "yes", "y"}


def green_space_filters(args):
    filters = {}
    for key, group_key in (("green_type", "green_space_type"),
                           ("maintenance_grade", "maintenance_grade"),
                           ("status", "green_space_status")):
        value = _enum(args, key, group_key)
        if value:
            filters[key] = value
    district = _text(args, "district")
    if district:
        filters["district"] = district
    keyword = _text(args, "keyword")
    if keyword:
        filters["keyword"] = keyword
    return filters


def task_filters(args):
    filters = {}
    green_space_id = _int(args, "green_space_id")
    if green_space_id:
        filters["green_space_id"] = green_space_id
    for key, group_key in (("status", "task_status"), ("task_type", "task_type"),
                           ("priority", "task_priority")):
        value = _enum(args, key, group_key)
        if value:
            filters[key] = value
    keyword = _text(args, "keyword")
    if keyword:
        filters["keyword"] = keyword
    filters["date_from"] = _date(args, "date_from")
    filters["date_to"] = _date(args, "date_to")
    filters["overdue"] = _flag(args, "overdue")
    filters["unplanned"] = _flag(args, "unplanned")
    # 仅看需要持证上岗的任务
    if _flag(args, "cert_required"):
        filters["cert_required"] = True
    cert_type = _enum(args, "required_cert_type", "cert_type")
    if cert_type:
        filters["required_cert_type"] = cert_type
    return filters


def record_filters(args):
    filters = {}
    for key in ("task_id", "green_space_id"):
        value = _int(args, key)
        if value:
            filters[key] = value
    filters["unlinked"] = _flag(args, "unlinked")
    for key, group_key in (("quality_result", "quality_result"), ("weather", "weather")):
        value = _enum(args, key, group_key)
        if value:
            filters[key] = value
    keyword = _text(args, "keyword")
    if keyword:
        filters["keyword"] = keyword
    filters["date_from"] = _date(args, "date_from")
    filters["date_to"] = _date(args, "date_to")
    return filters


def replacement_filters(args):
    filters = {}
    for key in ("green_space_id", "maintenance_record_id"):
        value = _int(args, key)
        if value:
            filters[key] = value
    for key, group_key in (("plant_category", "plant_category"), ("reason", "replacement_reason")):
        value = _enum(args, key, group_key)
        if value:
            filters[key] = value
    keyword = _text(args, "keyword")
    if keyword:
        filters["keyword"] = keyword
    filters["date_from"] = _date(args, "date_from")
    filters["date_to"] = _date(args, "date_to")
    return filters


def person_filters(args):
    filters = {}
    value = _enum(args, "status", "person_status")
    if value:
        filters["status"] = value
    team = _text(args, "team")
    if team:
        filters["team"] = team
    keyword = _text(args, "keyword")
    if keyword:
        filters["keyword"] = keyword
    return filters


def training_filters(args):
    filters = {}
    value = _enum(args, "category", "training_category")
    if value:
        filters["category"] = value
    trainer = _text(args, "trainer")
    if trainer:
        filters["trainer"] = trainer
    person_id = _int(args, "person_id")
    if person_id:
        filters["person_id"] = person_id
    keyword = _text(args, "keyword")
    if keyword:
        filters["keyword"] = keyword
    filters["date_from"] = _date(args, "date_from")
    filters["date_to"] = _date(args, "date_to")
    return filters


def certificate_filters(args):
    filters = {}
    person_id = _int(args, "person_id")
    if person_id:
        filters["person_id"] = person_id
    for key, group_key in (("cert_type", "cert_type"), ("status", "certificate_status")):
        value = _enum(args, key, group_key)
        if value:
            filters[key] = value
    # 派生时效过滤：valid / expiring / expired / revoked
    validity = _text(args, "validity")
    if validity in {"valid", "expiring", "expired", "revoked"}:
        filters["validity"] = validity
    keyword = _text(args, "keyword")
    if keyword:
        filters["keyword"] = keyword
    filters["expire_from"] = _date(args, "expire_from")
    filters["expire_to"] = _date(args, "expire_to")
    return filters
