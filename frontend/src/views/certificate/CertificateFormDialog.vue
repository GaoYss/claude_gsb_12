<template>
  <el-dialog :model-value="visible"
             :title="isEdit ? `编辑证书 · ${form.cert_no}` : '登记特种作业证书'"
             width="680px" top="7vh" destroy-on-close @update:model-value="close">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
      <el-form-item label="持证人" prop="person_id" :error="fieldErrors.person_id">
        <PersonSelect v-model="form.person_id" :preset="personPreset" include-inactive
                      placeholder="请选择持证人" />
      </el-form-item>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="证书类型" prop="cert_type" :error="fieldErrors.cert_type">
            <el-select v-model="form.cert_type" placeholder="请选择" style="width: 100%">
              <el-option v-for="item in certTypeOptions" :key="item.value"
                         :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="证书编号" prop="cert_no" :error="fieldErrors.cert_no">
            <el-input v-model="form.cert_no" placeholder="证书上的编号" maxlength="64" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="发证日期" prop="issue_date" :error="fieldErrors.issue_date">
            <el-date-picker v-model="form.issue_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选择日期" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="有效期至" prop="expire_date" :error="fieldErrors.expire_date">
            <el-date-picker v-model="form.expire_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="证书有效截止日" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="下次复审日" :error="fieldErrors.review_date">
            <el-date-picker v-model="form.review_date" type="date" value-format="YYYY-MM-DD"
                            placeholder="选填，临近复审会提醒" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="发证机关" :error="fieldErrors.issuer">
            <el-input v-model="form.issuer" placeholder="如：杭州市应急管理局" maxlength="128" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="登记状态" :error="fieldErrors.status">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="item in statusOptions" :key="item.value"
                         :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="备注" :error="fieldErrors.remark">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000"
                  placeholder="复审记录、换证说明等" />
      </el-form-item>
      <div class="form-hint">
        证书到期或复审日前 30 天系统会给出「即将到期」提醒；作业日超过有效期或复审日的任务不允许安排该人员。
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

import { certificateApi } from '@/api'
import PersonSelect from '@/components/common/PersonSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'

const emit = defineEmits(['saved'])

const { options: certTypeOptions } = useEnumOptions('cert_type')
const { options: statusOptions } = useEnumOptions('certificate_status')

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const editingId = ref(null)
const fieldErrors = ref({})
const personPreset = ref(null)
const form = reactive(emptyForm())

const isEdit = computed(() => editingId.value !== null)

const rules = {
  person_id: [{ required: true, message: '请选择持证人', trigger: 'change' }],
  cert_type: [{ required: true, message: '请选择证书类型', trigger: 'change' }],
  cert_no: [{ required: true, message: '请输入证书编号', trigger: 'blur' }],
  issue_date: [{ required: true, message: '请选择发证日期', trigger: 'change' }],
  expire_date: [{ required: true, message: '请选择有效期至', trigger: 'change' }],
}

function emptyForm() {
  return {
    cert_no: '',
    person_id: null,
    cert_type: 'electrician_low',
    issuer: '',
    issue_date: '',
    expire_date: '',
    review_date: '',
    status: 'active',
    remark: '',
  }
}

function open(row = null, person = null) {
  Object.assign(form, emptyForm())
  fieldErrors.value = {}
  personPreset.value = null
  editingId.value = row?.id ?? null
  if (row) {
    Object.keys(form).forEach((key) => {
      if (row[key] !== undefined && row[key] !== null) form[key] = row[key]
    })
    personPreset.value = row.person || person
  } else if (person) {
    form.person_id = person.id
    personPreset.value = person
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
  if (!payload.review_date) payload.review_date = null
  try {
    if (isEdit.value) {
      await certificateApi.update(editingId.value, payload)
      ElMessage.success('特种作业证书已更新')
    } else {
      await certificateApi.create(payload)
      ElMessage.success('特种作业证书登记成功')
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
