"""养护任务派工人员模型。"""

from ..extensions import db
from ..utils.dates import format_datetime
from .mixins import utcnow


class TaskWorker(db.Model):
    """任务派工明细：一条任务安排给哪些作业人员。

    安排持证作业时，service 层会逐人校验其对应特种作业证书是否在有效期内。
    """

    __tablename__ = "task_worker"
    __table_args__ = (
        db.UniqueConstraint("task_id", "worker_id", name="uq_task_worker"),
    )

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("maintenance_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_id = db.Column(
        db.Integer, db.ForeignKey("worker.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    task = db.relationship("MaintenanceTask", back_populates="workers")
    worker = db.relationship("Worker", back_populates="assignments", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "worker_id": self.worker_id,
            "worker": self.worker.to_brief() if self.worker else None,
            "created_at": format_datetime(self.created_at),
        }
