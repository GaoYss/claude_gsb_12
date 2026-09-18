<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑培训 · ${form.session_no}` : '登记培训记录'"
             width="860px" top="5vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-form-item label="培训主题" prop="topic" :error="fieldErrors.topic">
        <el-input v-model="form.topic" placeholder="如：高大乔木修剪与高空作业安全" maxlength="128" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item label="培训类别" prop="category" :error="fieldErrors.category">
            <el-select v-model="form.category" style="width: 100%">
              <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="培训日期" prop="train_date" :error="fieldErrors.train_date">
            <el-date-picker v-model="form.train_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="培训时长" :error="fieldErrors.duration_hours">
            <el-input-number v-model="form.duration_hours" :min="0.5" :max="240" :step="0.5"
                             controls-position="right" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="讲师" prop="trainer" :error="fieldErrors.trainer">
            <el-input v-model="form.trainer" placeholder="内训师 / 外聘讲师" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="组织单位" :error="fieldErrors.organization">
            <el-input v-model="form.organization" placeholder="如：安全管理科" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="培训地点" :error="fieldErrors.location">
            <el-input v-model="form.location" placeholder="会议室 / 实训场地" maxlength="128" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="培训内容" :error="fieldErrors.content">
        <el-input v-model="form.content" type="textarea" :rows="2" maxlength="4000"
                  placeholder="培训主要内容、教材与考核方式" />
      </el-form-item>

      <el-form-item label="参加人员" :error="attendeeError">
        <div class="attendee-block">
          <div class="attendee-picker">
            <WorkerSelect
              v-model="pickedIds"
              multiple
              :preset="pickedPresets"
              placeholder="搜索并添加参加人员（可多选）"
              @options-change="onOptionsLoaded"
            />
          </div>
          <el-table :data="attendees" size="small" border max-height="260" empty-text="尚未添加参加人员">
            <el-table-column label="姓名 / 工号" min-width="150">
              <template #default="{ row }">
                {{ row.name }}
                <span class="cell-sub">{{ row.employee_no }}</span>
              </template>
            </el-table-column>
            <el-table-column label="出勤情况" width="132">
              <template #default="{ row }">
                <el-select v-model="row.attendance" size="small" @change="onAttendanceChange(row)">
                  <el-option v-for="item in attendanceOptions" :key="item.value"
                             :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="考核结果" width="132">
              <template #default="{ row }">
                <el-select v-model="row.result" size="small" :disabled="row.attendance !== 'attended'">
                  <el-option v-for="item in resultOptions" :key="item.value"
                             :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="成绩" width="112">
              <template #default="{ row }">
                <el-input-number v-model="row.score" :min="0" :max="100" :step="1"
                                 size="small" controls-position="right"
                                 :disabled="row.attendance !== 'attended'" style="width: 100%" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="64">
              <template #default="{ row }">
                <el-button link type="danger" @click="removeAttendee(row)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="attendee-summary">
            已添加 <strong>{{ attendees.length }}</strong> 人，
            实际参训 <strong>{{ attendedCount }}</strong> 人，
            考核合格 <strong>{{ qualifiedCount }}</strong> 人
          </div>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { trainingApi } from '@/api'
import WorkerSelect from '@/components/common/WorkerSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: categoryOptions } = useEnumOptions('training_category')
const { options: attendanceOptions } = useEnumOptions('attendance_status')
const { options: resultOptions } = useEnumOptions('training_result')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const attendeeError = ref('')
const pickedIds = ref([])
const pickedPresets = ref([])
const attendees = ref([])
const workerCache = new Map()
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)
const attendedCount = computed(() => attendees.value.filter((item) => item.attendance === 'attended').length)
const qualifiedCount = computed(
  () => attendees.value.filter((item) => item.attendance === 'attended' && item.result === 'qualified').length
)

const rules = {
  topic: [{ required: true, message: '请输入培训主题', trigger: 'blur' }],
  category: [{ required: true, message: '请选择培训类别', trigger: 'change' }],
  train_date: [{ required: true, message: '请选择培训日期', trigger: 'change' }],
  trainer: [{ required: true, message: '请输入讲师', trigger: 'blur' }],
}

function emptyForm() {
  return {
    session_no: '',
    topic: '',
    category: 'safety',
    train_date: '',
    duration_hours: 2,
    location: '',
    trainer: '',
    organization: '',
    content: '',
    remark: '',
  }
}

function onOptionsLoaded(workers) {
  workers.forEach((person) => workerCache.set(person.id, person))
}

function onAttendanceChange(row) {
  if (row.attendance !== 'attended') {
    row.result = 'exempt'
    row.score = null
  } else if (row.result === 'exempt') {
    row.result = 'qualified'
  }
}

// 选择器勾选项变化时，把新增人员加入明细，移除的人员从明细删除
watch(pickedIds, (ids) => {
  const existingIds = new Set(attendees.value.map((item) => item.worker_id))
  ids.forEach((id) => {
    if (existingIds.has(id)) return
    const person = workerCache.get(id)
    attendees.value.push({
      worker_id: id,
      name: person?.name || `人员#${id}`,
      employee_no: person?.employee_no || '',
      attendance: 'attended',
      result: 'qualified',
      score: null,
    })
  })
  attendees.value = attendees.value.filter((row) => ids.includes(row.worker_id))
}, { deep: true })

function removeAttendee(row) {
  pickedIds.value = pickedIds.value.filter((id) => id !== row.worker_id)
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  attendeeError.value = ''
  attendees.value = []
  pickedIds.value = []
  pickedPresets.value = []
  workerCache.clear()
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
  }
  visible.value = true
  if (row?.attendees) {
    attendees.value = row.attendees.map((item) => ({
      worker_id: item.worker_id,
      name: item.worker?.name || `人员#${item.worker_id}`,
      employee_no: item.worker?.employee_no || '',
      attendance: item.attendance,
      result: item.result || 'exempt',
      score: item.score ?? null,
    }))
    pickedIds.value = attendees.value.map((item) => item.worker_id)
    pickedPresets.value = row.attendees
      .filter((item) => item.worker)
      .map((item) => ({ ...item.worker }))
    pickedPresets.value.forEach((person) => workerCache.set(person.id, person))
  }
}

function close() {
  visible.value = false
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  attendeeError.value = ''
  const payload = {
    ...form,
    attendees: attendees.value.map((row) => ({
      worker_id: row.worker_id,
      attendance: row.attendance,
      result: row.attendance === 'attended' ? row.result : 'exempt',
      score: row.attendance === 'attended' ? row.score : null,
    })),
  }
  if (!payload.session_no) delete payload.session_no
  submitting.value = true
  fieldErrors.value = {}
  try {
    if (isEdit.value) {
      await trainingApi.update(editingId.value, payload)
      ElMessage.success('培训记录已更新')
    } else {
      await trainingApi.create(payload)
      ElMessage.success('培训记录登记成功')
    }
    emit('saved')
    close()
  } catch (error) {
    fieldErrors.value = error?.details || {}
    if (fieldErrors.value.attendees) attendeeError.value = fieldErrors.value.attendees
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.attendee-block {
  width: 100%;
}

.attendee-picker {
  margin-bottom: 8px;
}

.attendee-summary {
  margin-top: 8px;
  color: #606266;
  font-size: 13px;
}

.attendee-summary strong {
  color: var(--gs-primary);
}

.cell-sub {
  color: #909399;
  font-size: 12px;
  margin-left: 6px;
}
</style>
