<template>
  <div class="page">
    <PageHeader title="人员培训记录" description="登记培训主题、时间、讲师与参加人员，记录出勤与考核结果，培训是持证上岗的基础台账">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记培训</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="培训编号 / 主题 / 讲师 / 地点" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.category" placeholder="培训类别" clearable @change="search">
          <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="培训日期起" end-placeholder="培训日期止" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 场培训，累计参训
          <strong>{{ summary?.attended_count ?? 0 }}</strong> 人次，
          考核合格 <strong>{{ summary?.qualified_count ?? 0 }}</strong> 人次
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column label="培训编号 / 主题" min-width="230" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cell-main">{{ row.topic }}</div>
            <div class="cell-sub">{{ row.session_no }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类别" width="120">
          <template #default="{ row }">
            <EnumTag group="training_category" :value="row.category" :label="row.category_label" />
          </template>
        </el-table-column>
        <el-table-column prop="train_date" label="培训日期" width="105" />
        <el-table-column label="时长" width="80">
          <template #default="{ row }">{{ row.duration_hours ?? '-' }} h</template>
        </el-table-column>
        <el-table-column prop="trainer" label="讲师" width="90">
          <template #default="{ row }">{{ row.trainer }}</template>
        </el-table-column>
        <el-table-column prop="location" label="地点" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.location || '-' }}</template>
        </el-table-column>
        <el-table-column label="参加情况" width="150">
          <template #default="{ row }">
            <div>应到 {{ row.attendee_count }} 人</div>
            <div class="cell-sub">实到 {{ row.attended_count }} · 合格 {{ row.qualified_count }}</div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="drawer.open(row.id)">详情</el-button>
            <el-button link type="primary" @click="edit(row)">编辑</el-button>
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
    <TrainingDetailDrawer ref="drawer" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { trainingApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'

import TrainingDetailDrawer from './TrainingDetailDrawer.vue'
import TrainingFormDialog from './TrainingFormDialog.vue'

const formDialog = ref(null)
const drawer = ref(null)
const dateRange = ref([])

const { options: categoryOptions } = useEnumOptions('training_category')

const { filters, meta, items, summary, loading, load, search, resetFilters,
  handlePageChange, handleSizeChange } = useListQuery(trainingApi.list, {
  initialFilters: { keyword: '', category: '', date_from: '', date_to: '' },
})

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

async function edit(row) {
  // 列表数据不含参加人员明细，编辑前先取详情
  const detail = await trainingApi.detail(row.id)
  formDialog.value.open(detail)
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除培训记录「${row.topic}」吗？参加人员明细将一并删除。`,
      '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
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

.cell-main {
  font-weight: 500;
}

.cell-sub {
  color: #909399;
  font-size: 12px;
}
</style>
