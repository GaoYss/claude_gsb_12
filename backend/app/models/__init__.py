"""模型包：导入全部模型，保证 db.create_all() 能建全表。"""

from .certificate import Certificate
from .green_space import GreenSpace
from .maintenance_record import MaintenanceRecord
from .maintenance_task import MaintenanceTask, TaskAssignee
from .person import Person
from .plant_replacement import PlantReplacement
from .training import TrainingAttendee, TrainingRecord

__all__ = [
    "GreenSpace",
    "MaintenanceTask",
    "TaskAssignee",
    "MaintenanceRecord",
    "PlantReplacement",
    "Person",
    "TrainingRecord",
    "TrainingAttendee",
    "Certificate",
]
