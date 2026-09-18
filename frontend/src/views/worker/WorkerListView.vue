<template>
  <div class="page">
    <PageHeader title="作业人员档案" description="管理人员花名册，作为培训签到、特种作业证书与任务派工的基础档案">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">新增人员</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="工号 / 姓名 / 班组 / 电话" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <el-input v-model="filters.team" placeholder="所属班组" clearable
                  @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.status" placeholder="在岗状态" clearable @change="search">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">共 <strong>{{ meta.total }}</strong> 名人员</span>
        <el-button :icon="'Refresh'" text @click="load">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column label="工号 / 姓名" min-width="150">
          <template #default="{ row }">
            <div class="cell-main">{{ row.name }}</div>
            <div class="cell-sub">{{ row.employee_no }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="team" label="所属班组" width="110">
          <template #default="{ row }">{{ row.team || '-' }}</template>
        </el-table-column>
        <el-table-column prop="position" label="岗位" width="110">
          <template #default="{ row }">{{ row.position || '-' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="联系电话" width="125">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="持证情况" width="150">
          <template #default="{ row }">
            <span>有效 <strong>{{ row.valid_certificate_count }}</strong> / {{ row.certificate_count }} 本</span>
            <el-tag v-if="row.expiring_certificate_count" type="warning" size="small" effect="plain">
              {{ row.expiring_certificate_count }} 本临期
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="hired_date" label="入职日期" width="110">
          <template #default="{ row }">{{ row.hired_date || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="86">
          <template #default="{ row }">
            <EnumTag group="worker_status" :value="row.status" :label="row.status_label" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
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

    <WorkerFormDialog ref="formDialog" @saved="load" />
    <WorkerDetailDrawer ref="drawer" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { workerApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'

import WorkerDetailDrawer from './WorkerDetailDrawer.vue'
import WorkerFormDialog from './WorkerFormDialog.vue'

const formDialog = ref(null)
const drawer = ref(null)

const { options: statusOptions } = useEnumOptions('worker_status')

const { filters, meta, items, loading, load, search, resetFilters, handlePageChange, handleSizeChange } =
  useListQuery(workerApi.list, {
    initialFilters: { keyword: '', team: '', status: '' },
  })

async function remove(row) {
  try {
    await workerApi.remove(row.id)
  } catch (error) {
    if (error?.status !== 409) return
    // 有关联的证书/培训/派工记录：二次确认后强制删除
    try {
      const counts = error.details || {}
      const detail = Object.entries(counts)
        .map(([, value]) => value)
      await ElMessageBox.confirm(
        `人员「${row.name}」已有证书、培训或派工记录（共 ${detail.reduce((a, b) => a + b, 0)} 条），删除将一并清除，是否继续？`,
        '删除确认', { type: 'warning', confirmButtonText: '强制删除', cancelButtonText: '取消' })
      await workerApi.remove(row.id, { force: true })
    } catch (confirmError) {
      if (confirmError === 'cancel' || confirmError === 'close') return
      return
    }
  }
  ElMessage.success('人员档案已删除')
  await load()
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
