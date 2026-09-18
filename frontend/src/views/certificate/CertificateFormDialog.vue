<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑证书 · ${form.cert_no}` : '登记特种作业证书'"
             width="600px" top="8vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-form-item label="持证人" prop="worker_id" :error="fieldErrors.worker_id">
        <WorkerSelect v-model="form.worker_id" :preset="workerPreset" placeholder="请选择持证人" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="证书类型" prop="cert_type" :error="fieldErrors.cert_type">
            <el-select v-model="form.cert_type" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="证书编号" prop="cert_no" :error="fieldErrors.cert_no">
            <el-input v-model="form.cert_no" placeholder="操作证编号" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="发证日期" prop="issue_date" :error="fieldErrors.issue_date">
            <el-date-picker v-model="form.issue_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择发证日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="有效期至" prop="expire_date" :error="fieldErrors.expire_date">
            <el-date-picker v-model="form.expire_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择到期日期" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="发证机关" :error="fieldErrors.issuing_authority">
        <el-input v-model="form.issuing_authority" placeholder="如：杭州市应急管理局" maxlength="128" />
      </el-form-item>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" />
      </el-form-item>
      <div class="form-hint">到期前 30 天系统会自动在「持证管理」与养护总览中给出临期提醒。</div>
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

import { certificateApi } from '@/api'
import WorkerSelect from '@/components/common/WorkerSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: typeOptions } = useEnumOptions('certificate_type')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const workerPreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  worker_id: [{ required: true, message: '请选择持证人', trigger: 'change' }],
  cert_type: [{ required: true, message: '请选择证书类型', trigger: 'change' }],
  cert_no: [{ required: true, message: '请输入证书编号', trigger: 'blur' }],
  issue_date: [{ required: true, message: '请选择发证日期', trigger: 'change' }],
  expire_date: [{ required: true, message: '请选择有效期至', trigger: 'change' }],
}

function emptyForm() {
  return {
    cert_no: '',
    worker_id: null,
    cert_type: 'aerial',
    issuing_authority: '',
    issue_date: '',
    expire_date: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  workerPreset.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    form.worker_id = row.worker_id
    workerPreset.value = row.worker || null
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
  try {
    if (isEdit.value) {
      await certificateApi.update(editingId.value, { ...form })
      ElMessage.success('证书信息已更新')
    } else {
      await certificateApi.create({ ...form })
      ElMessage.success('证书登记成功')
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
