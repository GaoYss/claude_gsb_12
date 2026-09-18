"""人员培训接口。"""

from flask import Blueprint, request

from ..schemas import training_filters, validate_training_session
from ..services import TrainingSessionService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("training_sessions", __name__)


@bp.get("/training-sessions")
def list_sessions():
    filters = training_filters(request.args)
    page, page_size = parse_page_args()
    query = TrainingSessionService.list_sessions(filters, request.args)
    data = paginate(query, page, page_size)
    data["summary"] = TrainingSessionService.summary(filters)
    return ok(data)


@bp.post("/training-sessions")
def create_session():
    payload = validate_training_session(json_body())
    session = TrainingSessionService.create(payload)
    return created(session.to_dict(detail=True), message="培训记录登记成功")


@bp.get("/training-sessions/<int:session_id>")
def get_session(session_id):
    return ok(TrainingSessionService.detail(session_id))


@bp.put("/training-sessions/<int:session_id>")
def update_session(session_id):
    payload = validate_training_session(json_body())
    session = TrainingSessionService.update(session_id, payload)
    return ok(session.to_dict(detail=True), message="培训记录已更新")


@bp.delete("/training-sessions/<int:session_id>")
def delete_session(session_id):
    TrainingSessionService.delete(session_id)
    return ok(None, message="培训记录已删除")
