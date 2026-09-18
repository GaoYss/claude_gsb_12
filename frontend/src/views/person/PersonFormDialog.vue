<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑人员 · ${form.employee_no}` : '新增人员档案'"
             width="600px" top="8vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="工号" prop="employee_no" :error="fieldErrors.employee_no">
            <el-input v-model="form.employee_no" placeholder="人事编号，如 P2026001" maxlength="32" />
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
            <el-input v-model="form.position" placeholder="如：绿化工 / 电工" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="联系电话" :error="fieldErrors.phone">
            <el-input v-model="form.phone" placeholder="选填" maxlength="32" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="人员状态" :error="fieldErrors.status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="入职日期" :error="fieldErrors.entry_date">
            <el-date-picker v-model="form.entry_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000"
                  placeholder="技能特长、证书情况说明等" />
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

import { personApi } from '@/api'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: statusOptions } = useEnumOptions('person_status')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  employee_no: [{ required: true, message: '请输入工号', trigger: 'blur' }],
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
    entry_date: '',
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
  try {
    if (isEdit.value) {
      await personApi.update(editingId.value, payload)
      ElMessage.success('人员档案已更新')
    } else {
      await personApi.create(payload)
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
