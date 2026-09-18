"""业务字典。

集中维护各模块的枚举选项：模型层用于入库校验与展示文案，
接口层通过 /api/v1/meta/enums 下发给前端，避免前后端重复定义。
"""


class EnumGroup:
    """一组枚举选项：value 入库，label 用于展示。"""

    def __init__(self, name, options):
        self.name = name
        self.options = [{"value": value, "label": label} for value, label in options]
        self._labels = {value: label for value, label in options}

    @property
    def values(self):
        return list(self._labels)

    def label(self, value):
        return self._labels.get(value, value)

    def has(self, value):
        return value in self._labels

    def default(self):
        return self.options[0]["value"]

    def __contains__(self, value):
        return value in self._labels


# ---------------------------------------------------------------- 绿地台账
GREEN_SPACE_TYPE = EnumGroup("green_space_type", [
    ("park", "公园绿地"),
    ("street", "街头游园"),
    ("road", "道路绿地"),
    ("residential", "居住区绿地"),
    ("attached", "单位附属绿地"),
    ("other", "其他绿地"),
])

MAINTENANCE_GRADE = EnumGroup("maintenance_grade", [
    ("level1", "一级养护"),
    ("level2", "二级养护"),
    ("level3", "三级养护"),
])

GREEN_SPACE_STATUS = EnumGroup("green_space_status", [
    ("normal", "正常养护"),
    ("repairing", "整治提升中"),
    ("suspended", "暂停养护"),
    ("archived", "已归档"),
])

# ---------------------------------------------------------------- 养护任务
TASK_TYPE = EnumGroup("task_type", [
    ("prune", "修剪整形"),
    ("water", "浇灌排涝"),
    ("fertilize", "施肥"),
    ("pest", "病虫害防治"),
    ("weed", "除草松土"),
    ("clean", "保洁清扫"),
    ("replant", "补植补种"),
    ("winter", "防寒防冻"),
    ("other", "其他养护"),
])

TASK_PRIORITY = EnumGroup("task_priority", [
    ("low", "低"),
    ("medium", "中"),
    ("high", "高"),
    ("urgent", "紧急"),
])

TASK_STATUS = EnumGroup("task_status", [
    ("pending", "待执行"),
    ("in_progress", "进行中"),
    ("completed", "已完成"),
    ("cancelled", "已取消"),
])

# ---------------------------------------------------------------- 养护记录
QUALITY_RESULT = EnumGroup("quality_result", [
    ("qualified", "合格"),
    ("pending", "待复检"),
    ("unqualified", "不合格"),
])

WEATHER = EnumGroup("weather", [
    ("sunny", "晴"),
    ("cloudy", "多云"),
    ("overcast", "阴"),
    ("rain", "雨"),
    ("snow", "雪"),
    ("windy", "大风"),
])

# ---------------------------------------------------------------- 绿植更换
PLANT_CATEGORY = EnumGroup("plant_category", [
    ("tree", "乔木"),
    ("shrub", "灌木"),
    ("flower", "草本花卉"),
    ("ground", "地被草坪"),
    ("vine", "藤本植物"),
    ("aquatic", "水生植物"),
])

REPLACEMENT_REASON = EnumGroup("replacement_reason", [
    ("dead", "枯死更换"),
    ("disease", "病虫害更换"),
    ("aging", "老化更新"),
    ("upgrade", "品种改造"),
    ("supplement", "补植补种"),
    ("design", "景观调整"),
])

OLD_PLANT_STATUS = EnumGroup("old_plant_status", [
    ("dead", "已枯死"),
    ("dying", "长势衰弱"),
    ("diseased", "感染病虫害"),
    ("aging", "老化退化"),
    ("normal", "长势正常"),
])

MEASURE_UNIT = EnumGroup("measure_unit", [
    ("plant", "株"),
    ("square_meter", "平方米"),
    ("pot", "盆"),
    ("clump", "丛"),
])

# ---------------------------------------------------------------- 人员档案
PERSON_STATUS = EnumGroup("person_status", [
    ("active", "在岗"),
    ("leave", "休假"),
    ("dispatched", "外借"),
    ("resigned", "离岗"),
])

# ---------------------------------------------------------------- 培训记录
TRAINING_CATEGORY = EnumGroup("training_category", [
    ("safety", "安全生产培训"),
    ("prejob", "岗前培训"),
    ("skill", "技能提升培训"),
    ("special", "特种作业培训"),
    ("regulation", "制度规范培训"),
    ("other", "其他培训"),
])

ATTENDANCE_STATUS = EnumGroup("attendance_status", [
    ("present", "已参加"),
    ("leave", "请假"),
    ("absent", "缺席"),
])

# ---------------------------------------------------------------- 特种作业证书
# 园林绿化养护涉及的特种作业 / 持证上岗类型
CERT_TYPE = EnumGroup("cert_type", [
    ("electrician_low", "低压电工作业"),
    ("electrician_high", "高压电工作业"),
    ("welding", "焊接与热切割作业"),
    ("height", "高处作业"),
    ("lifting", "起重机械作业"),
    ("forklift", "场内机动车辆作业"),
    ("pest_control", "有害生物防治作业"),
    ("other", "其他证书"),
])

# 证书登记状态（入库字段）
CERTIFICATE_STATUS = EnumGroup("certificate_status", [
    ("active", "在册"),
    ("revoked", "已注销"),
])

# 证书时效状态（按日期派生，不入库）
CERTIFICATE_VALIDITY = EnumGroup("certificate_validity", [
    ("valid", "有效"),
    ("expiring", "即将到期"),
    ("expired", "已过期"),
    ("revoked", "已注销"),
])

# 距到期（或复审日）不足该天数即视为「即将到期」
CERT_EXPIRE_SOON_DAYS = 30

# 前端下拉与文档共用的一份字典清单
ENUM_GROUPS = {
    "green_space_type": GREEN_SPACE_TYPE,
    "maintenance_grade": MAINTENANCE_GRADE,
    "green_space_status": GREEN_SPACE_STATUS,
    "task_type": TASK_TYPE,
    "task_priority": TASK_PRIORITY,
    "task_status": TASK_STATUS,
    "quality_result": QUALITY_RESULT,
    "weather": WEATHER,
    "plant_category": PLANT_CATEGORY,
    "replacement_reason": REPLACEMENT_REASON,
    "old_plant_status": OLD_PLANT_STATUS,
    "measure_unit": MEASURE_UNIT,
    "person_status": PERSON_STATUS,
    "training_category": TRAINING_CATEGORY,
    "attendance_status": ATTENDANCE_STATUS,
    "cert_type": CERT_TYPE,
    "certificate_status": CERTIFICATE_STATUS,
    "certificate_validity": CERTIFICATE_VALIDITY,
}


def all_enums():
    """返回全部字典，供前端下拉初始化。"""

    return {name: group.options for name, group in ENUM_GROUPS.items()}
