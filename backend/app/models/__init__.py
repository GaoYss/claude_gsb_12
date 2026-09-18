"""模型包：导入全部模型，保证 db.create_all() 能建全表。"""

from .certificate import Certificate
from .green_space import GreenSpace
from .maintenance_record import MaintenanceRecord
from .maintenance_task import MaintenanceTask
from .plant_replacement import PlantReplacement
from .task_worker import TaskWorker
from .training import TrainingAttendee, TrainingSession
from .worker import Worker

__all__ = [
    "GreenSpace",
    "MaintenanceTask",
    "MaintenanceRecord",
    "PlantReplacement",
    "Worker",
    "TrainingSession",
    "TrainingAttendee",
    "Certificate",
    "TaskWorker",
]
