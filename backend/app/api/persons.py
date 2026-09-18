"""人员档案接口。"""

from flask import Blueprint, request

from ..schemas import person_filters, validate_person
from ..services import PersonService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("persons", __name__)


@bp.get("/persons")
def list_persons():
    filters = person_filters(request.args)
    page, page_size = parse_page_args()
    query = PersonService.list_people(filters, request.args)
    data = paginate(query, page, page_size, serializer=PersonService.serialize_row)
    data["summary"] = PersonService.status_summary()
    return ok(data)


@bp.get("/persons/options")
def person_options():
    """在岗人员下拉，支持按姓名/工号搜索、按班组过滤。"""

    keyword = (request.args.get("keyword") or "").strip() or None
    team = (request.args.get("team") or "").strip() or None
    include_inactive = request.args.get("include_inactive", "").strip().lower() in {
        "1", "true", "yes", "y"
    }
    return ok({
        "items": PersonService.options(
            keyword=keyword, team=team, include_inactive=include_inactive
        )
    })


@bp.post("/persons")
def create_person():
    payload = validate_person(json_body())
    person = PersonService.create(payload)
    return created(person.to_dict(detail=True), message="人员档案创建成功")


@bp.get("/persons/<int:person_id>")
def get_person(person_id):
    return ok(PersonService.detail(person_id))


@bp.put("/persons/<int:person_id>")
def update_person(person_id):
    payload = validate_person(json_body())
    person = PersonService.update(person_id, payload)
    return ok(person.to_dict(detail=True), message="人员档案已更新")


@bp.delete("/persons/<int:person_id>")
def delete_person(person_id):
    result = PersonService.delete(person_id)
    return ok(result, message="人员档案已删除")
