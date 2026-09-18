<template>
  <el-drawer :model-value="visible" size="640px"
             :title="detail.name ? `人员档案 · ${detail.name}` : '人员档案'"
             @update:model-value="close">
    <div v-loading="loading" class="drawer-body">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="工号">{{ detail.employee_no }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ detail.name }}</el-descriptions-item>
        <el-descriptions-item label="班组">{{ detail.team || '-' }}</el-descriptions-item>
        <el-descriptions-item label="岗位">{{ detail.position || '-' }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ detail.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <EnumTag group="person_status" :value="detail.status" :label="detail.status_label" />
        </el-descriptions-item>
        <el-descriptions-item label="入职日期" :span="2">{{ detail.entry_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="table-toolbar">
        <span class="panel-title">特种作业证书（{{ (detail.certificates || []).length }}）</span>
        <el-button link type="primary" @click="goCertificates">证书管理</el-button>
      </div>
      <el-table :data="detail.certificates || []" size="small" border empty-text="暂无证书登记">
        <el-table-column prop="cert_type_label" label="证书类型" width="130" />
        <el-table-column prop="cert_no" label="证书编号" min-width="130" show-overflow-tooltip />
        <el-table-column label="有效期至" width="120">
          <template #default="{ row }">
            {{ row.deadline || row.expire_date }}
            <EnumTag v-if="row.validity !== 'valid'" group="certificate_validity"
                     :value="row.validity" :label="row.validity_label" />
          </template>
        </el-table-column>
      </el-table>

      <div class="table-toolbar">
        <span class="panel-title">培训履历（{{ (detail.trainings || []).length }}）</span>
        <el-button link type="primary" @click="goTrainings">培训记录</el-button>
      </div>
      <el-table :data="detail.trainings || []" size="small" border empty-text="暂无培训记录">
        <el-table-column prop="train_date" label="培训日期" width="110" />
        <el-table-column prop="topic" label="培训主题" min-width="160" show-overflow-tooltip />
        <el-table-column prop="trainer" label="讲师" width="100" show-overflow-tooltip />
        <el-table-column label="出席" width="90">
          <template #default="{ row }">
            <EnumTag group="attendance_status" :value="row.attendance" />
          </template>
        </el-table-column>
        <el-table-column prop="score" label="成绩" width="70">
          <template #default="{ row }">{{ row.score || '-' }}</template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { personApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'

const router = useRouter()
const visible = ref(false)
const loading = ref(false)
const detail = ref({})
const currentId = ref(null)

async function open(id) {
  currentId.value = id
  visible.value = true
  loading.value = true
  try {
    detail.value = await personApi.detail(id)
  } finally {
    loading.value = false
  }
}

function close() {
  visible.value = false
}

function goCertificates() {
  router.push({ path: '/certificates', query: { person_id: currentId.value } })
  close()
}

function goTrainings() {
  router.push({ path: '/trainings', query: { person_id: currentId.value } })
  close()
}

function validityTagType(validity) {
  return { expiring: 'warning', expired: 'danger', revoked: 'info' }[validity] || 'success'
}

defineExpose({ open })
</script>

<style scoped>
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-title {
  font-weight: 600;
}
</style>
