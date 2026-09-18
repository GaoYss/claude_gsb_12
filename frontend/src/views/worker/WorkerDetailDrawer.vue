<template>
  <el-drawer :model-value="visible" size="680px"
             :title="detail.employee_no ? `人员档案 · ${detail.name}` : '人员详情'"
             @update:model-value="close">
    <div v-loading="loading" class="drawer-body">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="工号">{{ detail.employee_no }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ detail.name }}</el-descriptions-item>
        <el-descriptions-item label="所属班组">{{ detail.team || '-' }}</el-descriptions-item>
        <el-descriptions-item label="岗位">{{ detail.position || '-' }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ detail.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <EnumTag group="worker_status" :value="detail.status" :label="detail.status_label" />
        </el-descriptions-item>
        <el-descriptions-item label="入职日期">{{ detail.hired_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="持证情况">
          有效 <strong>{{ detail.valid_certificate_count ?? 0 }}</strong> 本
          <el-tag v-if="detail.expiring_certificate_count" type="warning" size="small" effect="plain">
            {{ detail.expiring_certificate_count }} 本临期
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="table-toolbar">
        <span class="panel-title">特种作业证书（{{ detail.certificates?.length || 0 }}）</span>
        <el-button link type="primary" @click="goCertificates">登记/查看证书</el-button>
      </div>
      <el-table :data="detail.certificates || []" size="small" border empty-text="暂无证书">
        <el-table-column label="证书类型" min-width="130">
          <template #default="{ row }">{{ row.cert_type_label }}</template>
        </el-table-column>
        <el-table-column prop="cert_no" label="证书编号" width="130" />
        <el-table-column prop="expire_date" label="有效期至" width="110" />
        <el-table-column label="状态" width="92">
          <template #default="{ row }">
            <EnumTag group="certificate_status" :value="row.status" />
          </template>
        </el-table-column>
      </el-table>

      <div class="table-toolbar">
        <span class="panel-title">近期培训记录（{{ detail.training_records?.length || 0 }}）</span>
      </div>
      <el-table :data="detail.training_records || []" size="small" border empty-text="暂无培训记录">
        <el-table-column prop="train_date" label="培训日期" width="100" />
        <el-table-column prop="topic" label="培训主题" min-width="160" show-overflow-tooltip />
        <el-table-column label="出勤" width="80">
          <template #default="{ row }">
            <EnumTag group="attendance_status" :value="row.attendance" :label="row.attendance_label" />
          </template>
        </el-table-column>
        <el-table-column label="考核" width="92">
          <template #default="{ row }">
            <EnumTag group="training_result" :value="row.result" :label="row.result_label" />
          </template>
        </el-table-column>
      </el-table>

      <div class="table-toolbar">
        <span class="panel-title">近期派工任务（{{ detail.task_assignments?.length || 0 }}）</span>
      </div>
      <el-table :data="detail.task_assignments || []" size="small" border empty-text="暂无派工记录">
        <el-table-column prop="plan_date" label="计划日期" width="105" />
        <el-table-column prop="title" label="任务名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="持证要求" min-width="120">
          <template #default="{ row }">
            <span v-if="!row.required_cert_type" class="cell-sub">无特殊要求</span>
            <el-tag v-else type="warning" size="small" effect="plain">需持证</el-tag>
          </template>
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

import { workerApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'

const router = useRouter()

const visible = ref(false)
const loading = ref(false)
const detail = ref({})
const currentId = ref(null)

async function open(id) {
  currentId.value = id
  visible.value = true
  await load()
}

async function load() {
  if (!currentId.value) return
  loading.value = true
  try {
    detail.value = await workerApi.detail(currentId.value)
  } finally {
    loading.value = false
  }
}

function goCertificates() {
  router.push({ path: '/certificates', query: { worker_id: currentId.value } })
  close()
}

function close() {
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel-title {
  font-weight: 600;
}
</style>
