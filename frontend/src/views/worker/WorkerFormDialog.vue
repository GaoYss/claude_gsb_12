<template>
  <el-dialog :model-value="visible" :title="isEdit ? `编辑人员 · ${form.employee_no}` : '新增人员档案'"
             width="600px" top="8vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="96px">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="工号" :error="fieldErrors.employee_no">
            <el-input v-model="form.employee_no" placeholder="留空自动生成，如 WK-2026-0001" maxlength="32" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="姓名" prop="name" :error="fieldErrors.name">
            <el-input v-model="form.name" placeholder="请输入姓名" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="所属班组" :error="fieldErrors.team">
            <el-input v-model="form.team" placeholder="如：绿化一班" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="岗位" :error="fieldErrors.position">
            <el-input v-model="form.position" placeholder="如：高级绿化工" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="联系电话" :error="fieldErrors.phone">
            <el-input v-model="form.phone" placeholder="手机号码" maxlength="24" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="在岗状态" :error="fieldErrors.status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="入职日期" :error="fieldErrors.hired_date">
            <el-date-picker v-model="form.hired_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
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

import { workerApi } from '@/api'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: statusOptions } = useEnumOptions('worker_status')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

function emptyForm() {
  return {
    employee_no: '',
    name: '',
    team: '',
    position: '',
    phone: '',
    status: 'active',
    hired_date: '',
    remark: '',
  }
}

function open(row = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
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
  if (!payload.employee_no) delete payload.employee_no
  try {
    if (isEdit.value) {
      await workerApi.update(editingId.value, payload)
      ElMessage.success('人员档案已更新')
    } else {
      await workerApi.create(payload)
      ElMessage.success('人员档案创建成功')
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
