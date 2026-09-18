"""作业人员接口。"""

from flask import Blueprint, request

from ..schemas import validate_worker, worker_filters
from ..services import WorkerService
from ..utils.pagination import paginate, parse_page_args
from ..utils.requests import json_body, query_flag
from ..utils.responses import created, ok

bp = Blueprint("workers", __name__)


@bp.get("/workers")
def list_workers():
    filters = worker_filters(request.args)
    page, page_size = parse_page_args()
    query = WorkerService.list_workers(filters, request.args)
    data = paginate(query, page, page_size)
    return ok(data)


@bp.get("/workers/options")
def worker_options():
    """下拉选项：可按姓名/工号搜索，cert_type 时只返回持有该类有效证书的人员。"""

    keyword = (request.args.get("keyword") or "").strip() or None
    cert_type = (request.args.get("cert_type") or "").strip() or None
    return ok({"items": WorkerService.options(keyword=keyword, cert_type=cert_type)})


@bp.get("/workers/teams")
def worker_teams():
    return ok({"items": WorkerService.teams()})


@bp.post("/workers")
def create_worker():
    payload = validate_worker(json_body())
    worker = WorkerService.create(payload)
    return created(worker.to_dict(detail=True), message="人员档案创建成功")


@bp.get("/workers/<int:worker_id>")
def get_worker(worker_id):
    return ok(WorkerService.detail(worker_id))


@bp.put("/workers/<int:worker_id>")
def update_worker(worker_id):
    payload = validate_worker(json_body())
    worker = WorkerService.update(worker_id, payload)
    return ok(worker.to_dict(detail=True), message="人员档案已更新")


@bp.delete("/workers/<int:worker_id>")
def delete_worker(worker_id):
    """删除人员：已有证书/培训/派工记录时需 force=true 才级联删除。"""

    force = query_flag("force")
    result = WorkerService.delete(worker_id, force=force)
    return ok(result, message="人员档案已删除")
