<template>
  <div class="page">
    <PageHeader title="人员档案" description="养护作业人员台账：班组岗位、培训履历与特种作业持证情况">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">新增人员</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="姓名 / 工号 / 班组 / 岗位" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <el-input v-model="filters.team" placeholder="按班组" clearable
                  style="width: 160px" @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.status" placeholder="人员状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 人，
          在岗 <strong>{{ summary?.active ?? 0 }}</strong>、
          休假 <strong>{{ summary?.leave ?? 0 }}</strong>、
          外借 <strong>{{ summary?.dispatched ?? 0 }}</strong>、
          离岗 <strong>{{ summary?.resigned ?? 0 }}</strong>
        </span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column label="工号 / 姓名" min-width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="drawer.open(row.id)">{{ row.name }}</el-button>
            <div class="cell-sub">{{ row.employee_no }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="team" label="班组" width="110">
          <template #default="{ row }">{{ row.team || '-' }}</template>
        </el-table-column>
        <el-table-column prop="position" label="岗位" width="110">
          <template #default="{ row }">{{ row.position || '-' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="联系电话" width="130">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="证书" width="150">
          <template #default="{ row }">
            <span>{{ row.statistics.certificate_count }} 本</span>
            <el-tag v-if="row.statistics.active_certificate_count" type="success" size="small" effect="plain">
              在册 {{ row.statistics.active_certificate_count }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="培训" width="90">
          <template #default="{ row }">{{ row.statistics.training_count }} 场</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <EnumTag group="person_status" :value="row.status" :label="row.status_label" />
          </template>
        </el-table-column>
        <el-table-column prop="entry_date" label="入职日期" width="115">
          <template #default="{ row }">{{ row.entry_date || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="drawer.open(row.id)">档案</el-button>
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

    <PersonFormDialog ref="formDialog" @saved="load" />
    <PersonDetailDrawer ref="drawer" />
  </div>
</template>

<script setup>
import { ref } from 'vue'

import { personApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'
import { ElMessage, ElMessageBox } from 'element-plus'

import PersonDetailDrawer from './PersonDetailDrawer.vue'
import PersonFormDialog from './PersonFormDialog.vue'

const formDialog = ref(null)
const drawer = ref(null)

const { options: statusOptions } = useEnumOptions('person_status')

const { filters, meta, items, summary, loading, load, search, resetFilters,
  handlePageChange, handleSizeChange } = useListQuery(personApi.list, {
  initialFilters: { keyword: '', team: '', status: '' },
})

async function remove(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除人员「${row.name}」吗？删除后其培训签到与证书登记将一并清除；已安排任务的人员需先调整任务。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await personApi.remove(row.id)
    ElMessage.success('人员档案已删除')
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
