<template>
  <el-select
    :model-value="modelValue"
    filterable
    remote
    :multiple="multiple"
    clearable
    :remote-method="remoteSearch"
    :loading="loading"
    :placeholder="placeholder"
    :disabled="disabled"
    :style="{ width: '100%' }"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-option
      v-for="item in options"
      :key="item.id"
      :label="optionLabel(item)"
      :value="item.id"
    />
  </el-select>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'

import { workerApi } from '@/api'

const props = defineProps({
  modelValue: { type: [Number, String, Array], default: null },
  /** 单选传对象、多选择传数组，用于回显不在当前选项列表里的已选人员 */
  preset: { type: [Object, Array], default: null },
  placeholder: { type: String, default: '请选择人员' },
  disabled: { type: Boolean, default: false },
  multiple: { type: Boolean, default: false },
  /** 传入证书类型时，只返回持有该类有效证书的在岗人员 */
  certType: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'options-change'])

const options = ref([])
const loading = ref(false)

function optionLabel(item) {
  const team = item.team ? `（${item.team}）` : ''
  return item.employee_no ? `${item.employee_no} ${item.name}${team}` : item.name
}

function merge(items) {
  const map = new Map()
  items.filter(Boolean).forEach((item) => map.set(item.id, item))
  const presets = Array.isArray(props.preset) ? props.preset : props.preset ? [props.preset] : []
  presets.forEach((item) => map.set(item.id, item))
  options.value = [...map.values()]
  emit('options-change', options.value)
}

async function load(keyword) {
  loading.value = true
  try {
    const params = {}
    if (keyword) params.keyword = keyword
    if (props.certType) params.cert_type = props.certType
    const data = await workerApi.options(Object.keys(params).length ? params : undefined)
    merge(data?.items || [])
  } finally {
    loading.value = false
  }
}

function remoteSearch(keyword) {
  return load(keyword?.trim() || undefined)
}

watch(() => props.certType, () => load())
// preset 变化（编辑回显）时并入已有选项，不能把远程搜索结果清空
watch(() => props.preset, () => merge(options.value.map((item) => ({ ...item }))), { deep: true })

onMounted(() => load())
</script>
