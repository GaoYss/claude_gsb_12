"""人员培训记录接口。"""

from flask import Blueprint, request

from ..schemas import training_filters, validate_training
from ..services import TrainingRecordService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body
from ..utils.responses import created, ok

bp = Blueprint("trainings", __name__)


@bp.get("/trainings")
def list_trainings():
    filters = training_filters(request.args)
    page, page_size = parse_page_args()
    query = TrainingRecordService.list_trainings(filters, request.args)
    data = paginate(query, page, page_size, serializer=TrainingRecordService.serialize_row)
    data["summary"] = {"categories": TrainingRecordService.category_summary()}
    return ok(data)


@bp.post("/trainings")
def create_training():
    payload = validate_training(json_body())
    training = TrainingRecordService.create(payload)
    return created(training.to_dict(detail=True), message="培训记录登记成功")


@bp.get("/trainings/<int:training_id>")
def get_training(training_id):
    return ok(TrainingRecordService.detail(training_id))


@bp.put("/trainings/<int:training_id>")
def update_training(training_id):
    payload = validate_training(json_body())
    training = TrainingRecordService.update(training_id, payload)
    return ok(training.to_dict(detail=True), message="培训记录已更新")


@bp.delete("/trainings/<int:training_id>")
def delete_training(training_id):
    TrainingRecordService.delete(training_id)
    return ok(None, message="培训记录已删除")
