<template>
  <div class="page">
    <PageHeader title="特种作业持证管理" description="登记特种作业证书类型与有效期，临近到期自动提醒，安排持证任务时逐人校验">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open()">登记证书</el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="reminder.expiring.length || reminder.expired.length"
      class="reminder"
      :closable="false"
      :type="reminder.expired.length ? 'error' : 'warning'"
      show-icon
    >
      <template #title>
        <span>
          证书到期提醒（提前 {{ reminder.warning_days }} 天）：临近到期
          <strong>{{ reminder.expiring.length }}</strong> 本、已过期
          <strong>{{ reminder.expired.length }}</strong> 本 ——
          <el-button link type="primary" @click="jumpReminder('expiring')">查看临期</el-button>
          /
          <el-button link type="primary" @click="jumpReminder('expired')">查看过期</el-button>
        </span>
      </template>
    </el-alert>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="证书编号 / 持证人 / 发证机关" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <el-select v-model="filters.cert_type" placeholder="证书类型" clearable @change="search">
          <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select v-model="filters.status" placeholder="证书状态" clearable @change="search">
          <el-option label="有效" value="effective" />
          <el-option label="临近到期" value="expiring" />
          <el-option label="已过期" value="expired" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" unlink-panels value-format="YYYY-MM-DD"
                        start-placeholder="到期日起" end-placeholder="到期日止" @change="onDateChange" />
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 本证书，有效
          <strong>{{ summary?.effective ?? 0 }}</strong>、临期
          <strong>{{ summary?.expiring ?? 0 }}</strong>、过期
          <strong>{{ summary?.expired ?? 0 }}</strong>
        </span>
        <el-button :icon="'Refresh'" text @click="reloadAll">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column label="持证人" min-width="130">
          <template #default="{ row }">
            <div class="cell-main">{{ row.worker?.name || '-' }}</div>
            <div class="cell-sub">{{ row.worker?.employee_no || '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="证书类型" min-width="135">
          <template #default="{ row }">{{ row.cert_type_label }}</template>
        </el-table-column>
        <el-table-column prop="cert_no" label="证书编号" min-width="130" />
        <el-table-column prop="issuing_authority" label="发证机关" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.issuing_authority || '-' }}</template>
        </el-table-column>
        <el-table-column label="有效期" width="200">
          <template #default="{ row }">
            <div>{{ row.issue_date }} ~ {{ row.expire_date }}</div>
            <div class="cell-sub" :class="daysClass(row)">
              {{ daysText(row) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <EnumTag group="certificate_status" :value="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
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

    <CertificateFormDialog ref="formDialog" @saved="reloadAll" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { certificateApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'

import CertificateFormDialog from './CertificateFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)
const dateRange = ref([])
const reminder = reactive({ warning_days: 30, expiring: [], expired: [] })

const { options: typeOptions } = useEnumOptions('certificate_type')

const { filters, meta, items, summary, loading, load, search, resetFilters,
  handlePageChange, handleSizeChange } = useListQuery(certificateApi.list, {
  initialFilters: {
    keyword: '',
    cert_type: '',
    status: '',
    date_from: '',
    date_to: '',
    worker_id: route.query.worker_id ? Number(route.query.worker_id) : null,
  },
})

function onDateChange(value) {
  filters.date_from = value?.[0] || ''
  filters.date_to = value?.[1] || ''
  search()
}

async function loadReminders() {
  try {
    const data = await certificateApi.reminders()
    Object.assign(reminder, data)
  } catch {
    // 提醒加载失败不阻断列表使用
  }
}

async function reloadAll() {
  await Promise.all([load(), loadReminders()])
}

function jumpReminder(status) {
  filters.status = status
  search()
}

function daysText(row) {
  if (row.status === 'expired') return `已过期 ${Math.abs(row.days_to_expire)} 天`
  if (row.status === 'expiring') return `还有 ${row.days_to_expire} 天到期`
  return `还有 ${row.days_to_expire} 天到期`
}

function daysClass(row) {
  return {
    'days-expired': row.status === 'expired',
    'days-expiring': row.status === 'expiring',
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除证书「${row.cert_no}」吗？`, '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await certificateApi.remove(row.id)
    ElMessage.success('证书已删除')
    await reloadAll()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}

onMounted(loadReminders)
</script>

<style scoped>
.reminder {
  border-radius: 8px;
}

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

.days-expiring {
  color: #e6a23c;
}

.days-expired {
  color: #f56c6c;
}
</style>
