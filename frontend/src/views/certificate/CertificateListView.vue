<template>
  <div class="page">
    <PageHeader title="特种作业证书" description="登记证书类型与有效期，临近到期自动提醒；安排持证任务时校验有效性">
      <template #actions>
        <el-button type="primary" :icon="'Plus'" @click="formDialog.open(null, presetPerson)">登记证书</el-button>
      </template>
    </PageHeader>

    <!-- 到期提醒横幅 -->
    <div class="alert-grid">
      <el-alert
        :title="`${reminders.summary?.expired_count ?? 0} 本证书已过期（或逾期未复审），相关人员不得安排对应作业`"
        type="error" :closable="false" show-icon class="alert-item"
        @click="goFilter('expired')">
        <div v-if="reminders.expired?.length" class="alert-list">
          <span v-for="item in reminders.expired.slice(0, 4)" :key="item.id" class="alert-person">
            {{ item.person?.name }} · {{ item.cert_type_label }}（{{ item.deadline }}）
          </span>
        </div>
      </el-alert>
      <el-alert
        :title="`${reminders.summary?.expiring_count ?? 0} 本证书将在 ${reminders.summary?.days ?? 30} 天内到期/复审，请及时安排复审换证`"
        type="warning" :closable="false" show-icon class="alert-item"
        @click="goFilter('expiring')">
        <div v-if="reminders.expiring?.length" class="alert-list">
          <span v-for="item in reminders.expiring.slice(0, 4)" :key="item.id" class="alert-person">
            {{ item.person?.name }} · {{ item.cert_type_label }}（剩 {{ item.days_to_expire }} 天）
          </span>
        </div>
      </el-alert>
    </div>

    <div class="panel">
      <div class="filter-bar">
        <el-input v-model="filters.keyword" placeholder="证书编号 / 发证机关 / 持证人" clearable
                  :prefix-icon="'Search'" @keyup.enter="search" @clear="search" />
        <PersonSelect v-model="filters.person_id" placeholder="按持证人筛选"
                      include-inactive @update:model-value="search" />
        <el-select v-model="filters.cert_type" placeholder="证书类型" clearable @change="search">
          <el-option v-for="item in certTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-radio-group v-model="filters.validity" @change="search">
          <el-radio-button label="">全部</el-radio-button>
          <el-radio-button label="valid">有效</el-radio-button>
          <el-radio-button label="expiring">即将到期</el-radio-button>
          <el-radio-button label="expired">已过期</el-radio-button>
          <el-radio-button label="revoked">已注销</el-radio-button>
        </el-radio-group>
        <el-button type="primary" :icon="'Search'" @click="search">查询</el-button>
        <el-button :icon="'RefreshLeft'" @click="resetFilters">重置</el-button>
      </div>
    </div>

    <div class="panel">
      <div class="table-toolbar">
        <span class="summary-text">
          共 <strong>{{ meta.total }}</strong> 本，
          有效 <strong>{{ summary?.valid ?? 0 }}</strong>、
          即将到期 <strong class="text-warning">{{ summary?.expiring ?? 0 }}</strong>、
          已过期 <strong class="text-danger">{{ summary?.expired ?? 0 }}</strong>、
          已注销 <strong>{{ summary?.revoked ?? 0 }}</strong>
        </span>
        <el-button :icon="'Refresh'" text @click="reloadAll">刷新</el-button>
      </div>

      <el-table :data="items" v-loading="loading" border stripe>
        <el-table-column label="持证人" min-width="130">
          <template #default="{ row }">
            <div class="cell-main">{{ row.person?.name || '-' }}</div>
            <div class="cell-sub">{{ row.person?.employee_no }}{{ row.person?.team ? ' · ' + row.person.team : '' }}</div>
          </template>
        </el-table-column>
        <el-table-column label="证书类型" width="150">
          <template #default="{ row }">
            {{ row.cert_type_label }}
          </template>
        </el-table-column>
        <el-table-column prop="cert_no" label="证书编号" min-width="150" show-overflow-tooltip />
        <el-table-column prop="issuer" label="发证机关" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.issuer || '-' }}</template>
        </el-table-column>
        <el-table-column label="发证日期" width="110">
          <template #default="{ row }">{{ row.issue_date }}</template>
        </el-table-column>
        <el-table-column label="有效期 / 复审" width="170">
          <template #default="{ row }">
            <div>{{ row.expire_date }}</div>
            <div v-if="row.review_date" class="cell-sub">复审：{{ row.review_date }}</div>
          </template>
        </el-table-column>
        <el-table-column label="时效" width="110">
          <template #default="{ row }">
            <EnumTag group="certificate_validity" :value="row.validity" :label="row.validity_label" />
            <div v-if="row.status === 'active' && row.days_to_expire !== null"
                 class="cell-sub" :class="daysClass(row.validity)">
              {{ row.days_to_expire >= 0 ? `剩 ${row.days_to_expire} 天` : `已过期 ${-row.days_to_expire} 天` }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="formDialog.open(row)">编辑</el-button>
            <el-button v-if="row.status === 'active'" link type="warning" @click="revoke(row)">注销</el-button>
            <el-button v-else link type="success" @click="restore(row)">恢复</el-button>
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
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { certificateApi, personApi } from '@/api'
import EnumTag from '@/components/common/EnumTag.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import PersonSelect from '@/components/common/PersonSelect.vue'
import { useEnumOptions } from '@/composables/useEnumOptions'
import { useListQuery } from '@/composables/useListQuery'

import CertificateFormDialog from './CertificateFormDialog.vue'

const route = useRoute()
const formDialog = ref(null)

const { options: certTypeOptions } = useEnumOptions('cert_type')

const reminders = ref({ summary: { expired_count: 0, expiring_count: 0, days: 30 }, expired: [], expiring: [] })
const presetPerson = ref(null)

const { filters, meta, items, summary, loading, load, search, resetFilters,
  handlePageChange, handleSizeChange } = useListQuery(certificateApi.list, {
  initialFilters: {
    keyword: '',
    person_id: route.query.person_id ? Number(route.query.person_id) : null,
    cert_type: '',
    validity: '',
  },
})

async function loadReminders() {
  reminders.value = await certificateApi.reminders()
}

async function reloadAll() {
  await Promise.all([load(), loadReminders()])
}

function goFilter(validity) {
  filters.validity = validity
  search()
}

function daysClass(validity) {
  return { 'text-warning': validity === 'expiring', 'text-danger': validity === 'expired' }
}

async function revoke(row) {
  try {
    await ElMessageBox.confirm(
      `确认注销「${row.person?.name}」的${row.cert_type_label}（${row.cert_no}）吗？注销后该证书不再视为有效。`,
      '注销确认', { type: 'warning', confirmButtonText: '注销', cancelButtonText: '取消' },
    )
    await certificateApi.changeStatus(row.id, { status: 'revoked' })
    ElMessage.success('证书已注销')
    await reloadAll()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}

async function restore(row) {
  await certificateApi.changeStatus(row.id, { status: 'active' })
  ElMessage.success('证书已恢复在册')
  await reloadAll()
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除证书「${row.cert_no}」吗？此操作不可恢复。`,
      '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await certificateApi.remove(row.id)
    ElMessage.success('证书已删除')
    await reloadAll()
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
  }
}

onMounted(async () => {
  // 从人员档案带 person_id 跳转时，准备好持证人回显
  if (filters.person_id) {
    presetPerson.value = { id: filters.person_id }
    try {
      presetPerson.value = await personApi.detail(filters.person_id)
    } catch {
      // 忽略，表单仍可搜索选择
    }
  }
  loadReminders()
})
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

.text-warning {
  color: #e6a23c;
  font-weight: 600;
}

.text-danger {
  color: #f56c6c;
  font-weight: 600;
}

.alert-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 12px;
}

.alert-item {
  cursor: pointer;
}

.alert-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-top: 4px;
  font-size: 12px;
}

.alert-person {
  color: #606266;
}
</style>
