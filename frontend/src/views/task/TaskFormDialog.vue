<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑养护任务 · ${form.task_no}` : '登记养护任务'"
             width="760px" top="7vh" destroy-on-close @update:model-value="close">
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
                            placeholder="选择计划养护日期" style="width: 100%" />
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
        <el-col v-if="isEdit" :span="12">
          <el-form-item label="任务状态" :error="fieldErrors.status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="持证要求" :error="fieldErrors.required_cert_type">
        <el-select v-model="form.required_cert_type" clearable placeholder="无特殊持证要求"
                   style="width: 100%" @change="onCertTypeChange">
          <el-option v-for="item in certTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="作业人员" :error="fieldErrors.worker_ids">
        <WorkerSelect
          v-model="form.worker_ids"
          multiple
          :cert-type="form.required_cert_type || ''"
          :preset="workerPresets"
          :placeholder="form.required_cert_type ? '仅可选择证书在有效期内的人员' : '选择派工作业人员（可多选）'"
        />
        <div v-if="form.required_cert_type" class="cert-hint">
          <el-icon><WarningFilled /></el-icon>
          该任务为持证作业，仅列出持有「{{ certTypeLabel }}」且证书在计划作业日有效的人员；
          保存时后端会逐人复核，证书无效将无法派工。
        </div>
        <el-alert v-if="certBlockMessage" :title="certBlockMessage" type="error" :closable="false"
                  show-icon class="cert-alert" />
      </el-form-item>

      <el-form-item label="任务说明" :error="fieldErrors.description">
        <el-input v-model="form.description" type="textarea" :rows="3" maxlength="2000"
                  placeholder="作业范围、技术要求、注意事项等" />
      </el-form-item>
      <div class="form-hint">
        任务编号由系统按日自动生成；任务执行后可在「养护记录」中登记作业明细，任务状态会随之自动流转。
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

import { maintenanceTaskApi } from '@/api'
import GreenSpaceSelect from '@/components/common/GreenSpaceSelect.vue'
import WorkerSelect from '@/components/common/WorkerSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useMetaStore } from '@/stores/meta'
import { today } from '@/utils/format'

const emit = defineEmits(['saved'])

const { options: typeOptions } = useEnumOptions('task_type')
const { options: priorityOptions } = useEnumOptions('task_priority')
const { options: statusOptions } = useEnumOptions('task_status')
const { options: certTypeOptions } = useEnumOptions('certificate_type')
const metaStore = useMetaStore()

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const certBlockMessage = ref('')
const spacePreset = ref(null)
const workerPresets = ref([])
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)
const certTypeLabel = computed(() =>
  metaStore.label('certificate_type', form.required_cert_type))

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
    required_cert_type: null,
    worker_ids: [],
    status: 'pending',
    description: '',
  }
}

function onCertTypeChange() {
  // 切换持证要求后清空已选人员，避免保留不满足新证书要求的人员
  form.worker_ids = []
  workerPresets.value = []
  certBlockMessage.value = ''
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  certBlockMessage.value = ''
  spacePreset.value = null
  workerPresets.value = []
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    form.green_space_id = row.green_space_id
    spacePreset.value = row.green_space || null
    form.required_cert_type = row.required_cert_type || null
    form.worker_ids = (row.workers || []).map((item) => item.worker_id)
    workerPresets.value = (row.workers || []).map((item) => item.worker).filter(Boolean)
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
  certBlockMessage.value = ''
  const payload = { ...form, worker_ids: [...form.worker_ids] }
  if (!payload.required_cert_type) payload.required_cert_type = null
  if (!payload.task_no) delete payload.task_no
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
    if (error?.status === 409) {
      certBlockMessage.value = error.message
    }
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.cert-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  color: #b88230;
  font-size: 12px;
  line-height: 1.5;
}

.cert-alert {
  margin-top: 8px;
}
</style>
