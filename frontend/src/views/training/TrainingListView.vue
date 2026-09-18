<template>
  <div class="page">
    <PageHeader title="人员培训记录" description="登记培训主题、时间、讲师与参加人员，留存培训与签到台账">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记培训</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="培训主题 / 编号 / 讲师 / 地点" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.category" placeholder="培训类别" clearable @change="search">
          <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <PersonSelect v-model="filters.person_id" placeholder="按参加人员筛选"
                      include-inactive @update:model-value="search" />
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="培训开始" end-placeholder="培训结束" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">共 <strong>{{ meta.total }}</strong> 场培训</span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column label="培训编号 / 主题" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="detailDialog.open(row.id)">{{ row.topic }}</el-button>
            <div class="cell-sub">{{ row.training_no }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类别" width="130">
          <template #default="{ row }">
            <EnumTag group="training_category" :value="row.category" :label="row.category_label" />
          </template>
        </el-table-column>
        <el-table-column prop="train_date" label="培训日期" width="115" />
        <el-table-column prop="trainer" label="讲师" width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.trainer }}</template>
        </el-table-column>
        <el-table-column prop="location" label="地点" width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.location || '-' }}</template>
        </el-table-column>
        <el-table-column label="学时" width="80">
          <template #default="{ row }">{{ row.duration_hours ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="参加情况" width="130">
          <template #default="{ row }">
            <div>{{ row.attendee_count }} 人</div>
            <div class="cell-sub">已参加 {{ row.present_count }} 人</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="detailDialog.open(row.id)">详情</el-button>
            <el-button link type="primary" @click="formDialog.open(row)">编辑</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="meta.total"
        :current-page="meta.page"
        :page-size="meta.page_size"
        :page-sizes="[10, 20, 50]"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>

    <TrainingFormDialog ref="formDialog" @saved="load" />
    <TrainingDetailDialog ref="detailDialog" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { trainingApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import PersonSelect from '@/components/common/PersonSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'

import TrainingDetailDialog from './TrainingDetailDialog.vue'
import TrainingFormDialog from './TrainingFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const detailDialog = ref(null)
const dateRange = ref([])

const { options: categoryOptions } = useEnumOptions('training_category')

const { filters, meta, items, loading, load, search, resetFilters,
  handlePageChange, handleSizeChange } = useListQuery(trainingApi.list, {
  initialFilters: {
    keyword: '',
    category: '',
    person_id: route.query.person_id ? Number(route.query.person_id) : null,
    date_from: '',
    date_to: '',
  },
})

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除培训记录「${row.topic}」吗？参加人员签到将一并删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await trainingApi.remove(row.id)
    ElMessage.success('培训记录已删除')
    await load()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}
</script>

<style scoped>
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.cell-sub {
  color: #909399;
  font-size: 12px;
}
</style>
