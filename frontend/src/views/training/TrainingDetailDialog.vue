<template>
  <el-dialog :model-value="visible"
             :title="detail.training_no ? `培训记录 · ${detail.training_no}` : '培训记录详情'"
             width="760px" top="7vh" destroy-on-close @update:model-value="close">
    <div v-loading="loading" class="detail-body">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="培训主题" :span="2">{{ detail.topic }}</el-descriptions-item>
        <el-descriptions-item label="培训类别">
          <EnumTag group="training_category" :value="detail.category" :label="detail.category_label" />
        </el-descriptions-item>
        <el-descriptions-item label="培训日期">{{ detail.train_date }}</el-descriptions-item>
        <el-descriptions-item label="讲师">{{ detail.trainer }}</el-descriptions-item>
        <el-descriptions-item label="培训学时">
          {{ detail.duration_hours !== null && detail.duration_hours !== undefined
            ? `${detail.duration_hours} 学时` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="培训地点" :span="2">{{ detail.location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="培训内容" :span="2">{{ detail.content || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <div class="table-toolbar">
        <span class="panel-title">
          参加人员（{{ detail.attendee_count ?? (detail.attendees || []).length }} 人，
          已参加 {{ detail.present_count ?? presentCount }} 人）
        </span>
      </div>
      <el-table :data="detail.attendees || []" size="small" border empty-text="未登记参加人员">
        <el-table-column label="姓名" width="130">
          <template #default="{ row }">{{ row.person?.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="工号" width="120">
          <template #default="{ row }">{{ row.person?.employee_no || '-' }}</template>
        </el-table-column>
        <el-table-column label="班组" min-width="110">
          <template #default="{ row }">{{ row.person?.team || '-' }}</template>
        </el-table-column>
        <el-table-column label="出席情况" width="100">
          <template #default="{ row }">
            <EnumTag group="attendance_status" :value="row.attendance" :label="row.attendance_label" />
          </template>
        </el-table-column>
        <el-table-column label="成绩/评价" width="110">
          <template #default="{ row }">{{ row.score || '-' }}</template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <el-button @click="close">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'

import { trainingApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'

const visible = ref(false)
const loading = ref(false)
const detail = ref({})

const presentCount = computed(() =>
  (detail.value.attendees || []).filter((item) => item.attendance === 'present').length,
)

async function open(id) {
  visible.value = true
  loading.value = true
  try {
    detail.value = await trainingApi.detail(id)
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
.detail-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel-title {
  font-weight: 600;
}
</style>
