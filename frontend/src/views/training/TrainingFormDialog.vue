<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑培训记录 · ${form.training_no}` : '登记培训记录'"
             width="820px" top="5vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-row :gutter="16">
        <el-col :span="14">
          <el-form-item label="培训主题" prop="topic" :error="fieldErrors.topic">
            <el-input v-model="form.topic" placeholder="如：高处作业安全操作培训" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="10">
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
          <el-form-item label="讲师" prop="trainer" :error="fieldErrors.trainer">
            <el-input v-model="form.trainer" placeholder="内训师 / 外聘讲师" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="培训学时" :error="fieldErrors.duration_hours">
            <el-input-number v-model="form.duration_hours" :min="0.5" :max="99" :precision="1"
                             :step="0.5" :controls="false" placeholder="如 4" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="24">
          <el-form-item label="培训地点" :error="fieldErrors.location">
            <el-input v-model="form.location" placeholder="如：单位多功能厅" maxlength="128" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="培训内容" :error="fieldErrors.content">
        <el-input v-model="form.content" type="textarea" :rows="2" maxlength="4000"
                  placeholder="培训大纲、考核方式等" />
      </el-form-item>

      <el-form-item label="参加人员" :error="fieldErrors.attendees">
        <div class="attendee-block">
          <PersonSelect v-model="selectedIds" multiple :preset="personPreset"
                        include-inactive
                        placeholder="选择参加培训的人员（可多选）" @items-change="onItemsChange" />
          <div v-if="attendeeRows.length" class="attendee-summary">
            已选 {{ attendeeRows.length }} 人，
            其中已参加 <strong>{{ presentCount }}</strong> 人
          </div>
          <el-table v-if="attendeeRows.length" :data="attendeeRows" size="small" border>
            <el-table-column label="姓名" width="150">
              <template #default="{ row }">{{ row.name }}<span class="cell-sub">（{{ row.employee_no }}）</span></template>
            </el-table-column>
            <el-table-column label="班组" min-width="110">
              <template #default="{ row }">{{ row.team || '-' }}</template>
            </el-table-column>
            <el-table-column label="出席情况" width="150">
              <template #default="{ row }">
                <el-select v-model="row.attendance" size="small">
                  <el-option v-for="item in attendanceOptions" :key="item.value"
                             :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="成绩/评价" width="130">
              <template #default="{ row }">
                <el-input v-model="row.score" size="small" maxlength="32"
                          :disabled="row.attendance !== 'present'" placeholder="如 92 / 合格" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ $index }">
                <el-button link type="danger" size="small" @click="removeAttendee($index)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-form-item>

      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { trainingApi } from '@/api'
import PersonSelect from '@/components/common/PersonSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: categoryOptions } = useEnumOptions('training_category')
const { options: attendanceOptions } = useEnumOptions('attendance_status')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const form = reactive(emptyForm())

// 已选人员行：{person_id, name, employee_no, team, attendance, score}
const attendeeRows = ref([])
const selectedIds = ref([])
// 供 PersonSelect 回显已选人员
const personPreset = ref([])

const isEdit = computed(() => editingId.value !== null)
const presentCount = computed(() => attendeeRows.value.filter((r) => r.attendance === 'present').length)

const rules = {
  topic: [{ required: true, message: '请输入培训主题', trigger: 'blur' }],
  train_date: [{ required: true, message: '请选择培训日期', trigger: 'change' }],
  trainer: [{ required: true, message: '请输入讲师', trigger: 'blur' }],
}

// 多选变化的唯一入口：按选中人员重建行，保留已设置的出席情况与成绩
function onItemsChange(people) {
  const previous = new Map(attendeeRows.value.map((row) => [row.person_id, row]))
  attendeeRows.value = people.map((person) => {
    const old = previous.get(person.id)
    return {
      person_id: person.id,
      name: person.name,
      employee_no: person.employee_no,
      team: person.team || '',
      attendance: old?.attendance || 'present',
      score: old?.score || '',
    }
  })
}

function emptyForm() {
  return {
    training_no: '',
    topic: '',
    category: 'safety',
    train_date: today(),
    location: '',
    trainer: '',
    duration_hours: 4,
    content: '',
    remark: '',
  }
}

function removeAttendee(index) {
  const row = attendeeRows.value[index]
  attendeeRows.value.splice(index, 1)
  selectedIds.value = selectedIds.value.filter((id) => id !== row.person_id)
}

async function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  attendeeRows.value = []
  selectedIds.value = []
  personPreset.value = []
  editingId.value = row?.id ?? null
  if (row) {
    // 列表行不含人员明细，编辑时拉详情
    const detail = row.attendees ? row : await trainingApi.detail(row.id)
    Object.keys(form).forEach((key) => {
      if (detail[key] !== undefined && detail[key] !== null) form[key] = detail[key]
    })
    attendeeRows.value = (detail.attendees || []).map((item) => ({
      person_id: item.person_id,
      name: item.person?.name || '',
      employee_no: item.person?.employee_no || '',
      team: item.person?.team || '',
      attendance: item.attendance,
      score: item.score || '',
    }))
    selectedIds.value = attendeeRows.value.map((r) => r.person_id)
    personPreset.value = (detail.attendees || []).map((item) => item.person).filter(Boolean)
  }
  visible.value = true
}

function close() {
  visible.value = false
}

async function submit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  fieldErrors.value = {}
  const payload = {
    ...form,
    attendees: attendeeRows.value.map((row) => ({
      person_id: row.person_id,
      attendance: row.attendance,
      score: row.attendance === 'present' ? row.score || null : null,
    })),
  }
  if (!payload.training_no) delete payload.training_no
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
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.attendee-block {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attendee-summary {
  color: #606266;
  font-size: 13px;
}

.cell-sub {
  color: #909399;
  font-size: 12px;
}
</style>
