<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑养护任务 · ${form.task_no}` : '登记养护任务'"
             width="760px" top="6vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="所属绿地" prop="green_space_id" :error="fieldErrors.green_space_id">
        <GreenSpaceSelect v-model="form.green_space_id" :preset="spacePreset" placeholder="请选择绿地" />
      </el-form-item>
      <el-form-item label="任务名称" prop="title" :error="fieldErrors.title">
        <el-input v-model="form.title" placeholder="如：行道树整形修剪" maxlength="128" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="养护类型" prop="task_type" :error="fieldErrors.task_type">
            <el-select v-model="form.task_type" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="计划日期" prop="plan_date" :error="fieldErrors.plan_date">
            <el-date-picker v-model="form.plan_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择计划养护日期" style="width: 100%"
                            @change="scheduleCertCheck" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="优先级" :error="fieldErrors.priority">
            <el-select v-model="form.priority" style="width: 100%">
              <el-option v-for="item in priorityOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="执行班组" :error="fieldErrors.executor">
            <el-input v-model="form.executor" placeholder="如：绿化一班" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="持证要求" :error="fieldErrors.required_cert_type">
            <el-select v-model="form.required_cert_type" clearable placeholder="普通作业无需持证"
                       style="width: 100%" @change="onCertRequirementChange">
              <el-option v-for="item in certTypeOptions" :key="item.value"
                         :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col v-if="isEdit" :span="12">
          <el-form-item label="任务状态" :error="fieldErrors.status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item v-if="form.required_cert_type" label="作业人员"
                    :error="fieldErrors.assignee_ids">
        <div class="assignee-block">
          <PersonSelect v-model="form.assignee_ids" multiple :preset="assigneePreset"
                        placeholder="选择持对应证书的作业人员" @items-change="onAssigneeItemsChange" />
          <div v-if="certChecks.length" class="cert-check-list">
            <div v-for="item in certChecks" :key="item.person_id"
                 class="cert-check-item" :class="item.valid ? 'is-valid' : 'is-invalid'">
              <el-icon><CircleCheck v-if="item.valid" /><CircleClose v-else /></el-icon>
              <span class="cert-check-name">{{ item.person.name }}</span>
              <span class="cert-check-text">
                <template v-if="item.certificate">
                  {{ item.certificate.cert_no }} · {{ item.certificate.cert_type_label }}
                  （{{ item.valid ? `有效至 ${item.certificate.deadline}` : buildInvalidText(item.certificate) }}）
                </template>
                <template v-else>
                  未持有{{ certTypeLabel }}
                </template>
              </span>
            </div>
          </div>
          <el-alert v-if="form.required_cert_type && !form.assignee_ids?.length"
                    type="warning" :closable="false" show-icon
                    title="该任务要求持证上岗，请选择持有效证书的作业人员" />
          <el-alert v-else-if="hasInvalidCert" type="error" :closable="false" show-icon
                    title="存在证书不符合要求的人员，作业日当天不能上岗，保存时将被后端拦截" />
        </div>
      </el-form-item>

      <el-form-item label="任务说明" :error="fieldErrors.description">
        <el-input v-model="form.description" type="textarea" :rows="3" maxlength="2000"
                  placeholder="作业范围、技术要求、注意事项等" />
      </el-form-item>
      <div class="form-hint">
        任务编号由系统按日自动生成；选择持证要求后，作业人员需在计划作业日持对应有效证书，
        证书临近到期会在「特种作业证书」页面提醒。
      </div>
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

import { certificateApi, maintenanceTaskApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import PersonSelect from '@/components/common/PersonSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useMetaStore } from '@/stores/meta'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: typeOptions } = useEnumOptions('task_type')
const { options: priorityOptions } = useEnumOptions('task_priority')
const { options: statusOptions } = useEnumOptions('task_status')
const { options: certTypeOptions } = useEnumOptions('cert_type')
const metaStore = useMetaStore()

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const spacePreset = ref(null)
const assigneePreset = ref([])
const certChecks = ref([])
let checkTimer = null
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)
const hasInvalidCert = computed(() => certChecks.value.some((item) => !item.valid))
const certTypeLabel = computed(() =>
  metaStore.label('cert_type', form.required_cert_type),
)

const rules = {
  green_space_id: [{ required: true, message: '请选择所属绿地', trigger: 'change' }],
  title: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  task_type: [{ required: true, message: '请选择养护类型', trigger: 'change' }],
  plan_date: [{ required: true, message: '请选择计划日期', trigger: 'change' }],
}

function emptyForm() {
  return {
    task_no: '',
    green_space_id: null,
    title: '',
    task_type: 'prune',
    plan_date: today(),
    priority: 'medium',
    executor: '',
    status: 'pending',
    required_cert_type: '',
    assignee_ids: [],
    description: '',
  }
}

function buildInvalidText(certificate) {
  if (certificate.status === 'revoked') return '证书已注销'
  if (certificate.validity === 'expired') return `已于 ${certificate.deadline} 到期`
  if (certificate.validity === 'expiring') return `作业日晚于 ${certificate.deadline}`
  return '作业日无效'
}

function onAssigneeItemsChange(people) {
  assigneePreset.value = people
  scheduleCertCheck()
}

function onCertRequirementChange() {
  certChecks.value = []
  scheduleCertCheck()
}

function scheduleCertCheck() {
  if (checkTimer) clearTimeout(checkTimer)
  checkTimer = setTimeout(runCertCheck, 250)
}

async function runCertCheck() {
  if (!form.required_cert_type || !form.assignee_ids?.length || !form.plan_date) {
    certChecks.value = []
    return
  }
  try {
    const data = await certificateApi.check({
      cert_type: form.required_cert_type,
      person_ids: form.assignee_ids.join(','),
      plan_date: form.plan_date,
    })
    certChecks.value = data?.items || []
  } catch {
    // 预校验失败不阻塞编辑，保存时以后端校验为准
    certChecks.value = []
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  spacePreset.value = null
  assigneePreset.value = []
  certChecks.value = []
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    form.green_space_id = row.green_space_id
    form.required_cert_type = row.required_cert_type || ''
    form.assignee_ids = row.assignee_person_ids || []
    spacePreset.value = row.green_space || null
    assigneePreset.value = (row.assignees || []).map((item) => item.person).filter(Boolean)
    if (form.required_cert_type && form.assignee_ids.length) scheduleCertCheck()
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
  const payload = { ...form }
  if (!payload.task_no) delete payload.task_no
  if (!payload.required_cert_type) payload.required_cert_type = null
  try {
    if (isEdit.value) {
      await maintenanceTaskApi.update(editingId.value, payload)
      ElMessage.success('养护任务已更新')
    } else {
      await maintenanceTaskApi.create(payload)
      ElMessage.success('养护任务登记成功')
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
.assignee-block {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cert-check-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cert-check-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 13px;
}

.cert-check-item.is-valid {
  background: #f0f9eb;
  color: #67c23a;
}

.cert-check-item.is-invalid {
  background: #fef0f0;
  color: #f56c6c;
}

.cert-check-name {
  font-weight: 600;
}

.cert-check-text {
  color: #606266;
}
</style>
