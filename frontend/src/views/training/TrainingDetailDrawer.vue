<template>
  <el-drawer :model-value="visible" size="720px"
             :title="detail.session_no ? `培训记录 · ${detail.session_no}` : '培训详情'"
             @update:model-value="close">
    <div v-loading="loading" class="drawer-body">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="培训主题" :span="2">{{ detail.topic }}</el-descriptions-item>
        <el-descriptions-item label="培训类别">
          <EnumTag group="training_category" :value="detail.category" :label="detail.category_label" />
        </el-descriptions-item>
        <el-descriptions-item label="培训日期">{{ detail.train_date }}</el-descriptions-item>
        <el-descriptions-item label="讲师">{{ detail.trainer }}</el-descriptions-item>
        <el-descriptions-item label="时长">{{ detail.duration_hours ?? '-' }} 小时</el-descriptions-item>
        <el-descriptions-item label="组织单位">{{ detail.organization || '-' }}</el-descriptions-item>
        <el-descriptions-item label="培训地点">{{ detail.location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="培训内容" :span="2">{{ detail.content || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="table-toolbar">
        <span class="panel-title">
          参加人员（应到 {{ detail.attendee_count ?? 0 }} 人，
          实到 {{ detail.attended_count ?? 0 }} 人，
          合格 {{ detail.qualified_count ?? 0 }} 人）
        </span>
      </div>
      <el-table :data="detail.attendees || []" size="small" border empty-text="未登记参加人员">
        <el-table-column label="姓名 / 工号" min-width="150">
          <template #default="{ row }">
            {{ row.worker?.name || '-' }}
            <span class="cell-sub">{{ row.worker?.employee_no || '' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="班组" width="100">
          <template #default="{ row }">{{ row.worker?.team || '-' }}</template>
        </el-table-column>
        <el-table-column label="出勤" width="90">
          <template #default="{ row }">
            <EnumTag group="attendance_status" :value="row.attendance" :label="row.attendance_label" />
          </template>
        </el-table-column>
        <el-table-column label="考核结果" width="100">
          <template #default="{ row }">
            <EnumTag group="training_result" :value="row.result" :label="row.result_label" />
          </template>
        </el-table-column>
        <el-table-column label="成绩" width="70">
          <template #default="{ row }">{{ row.score ?? '-' }}</template>
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

import { trainingApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'

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
    detail.value = await trainingApi.detail(currentId.value)
  } finally {
    loading.value = false
  }
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

.cell-sub {
  color: #909399;
  font-size: 12px;
  margin-left: 6px;
}
</style>
