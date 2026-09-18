<template>
  <el-select
    :model-value="modelValue"
    filterable
    remote
    :multiple="multiple"
    :collapse-tags="multiple"
    :collapse-tags-tooltip="multiple"
    clearable
    :remote-method="remoteSearch"
    :loading="loading"
    :placeholder="placeholder"
    :disabled="disabled"
    :style="{ width: '100%' }"
    @update:model-value="onChange"
  >
    <el-option
      v-for="item in options"
      :key="item.id"
      :label="`${item.name}（${item.employee_no}${item.team ? ' · ' + item.team : ''}）`"
      :value="item.id"
    />
  </el-select>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'

import { personApi } from '@/api'

const props = defineProps({
  modelValue: { type: [Number, String, Array], default: null },
  preset: { type: [Object, Array], default: null },
  placeholder: { type: String, default: '请选择人员' },
  disabled: { type: Boolean, default: false },
  multiple: { type: Boolean, default: false },
  includeInactive: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'items-change'])

const options = ref([])
const loading = ref(false)

function merge(items) {
  const map = new Map()
  items.filter(Boolean).forEach((item) => map.set(item.id, item))
  if (props.preset) {
    const presets = Array.isArray(props.preset) ? props.preset : [props.preset]
    presets.filter(Boolean).forEach((item) => map.set(item.id, item))
  }
  options.value = [...map.values()]
}

function onChange(value) {
  emit('update:modelValue', value)
  if (props.multiple) {
    const values = Array.isArray(value) ? value : []
    const map = new Map(options.value.map((item) => [item.id, item]))
    emit('items-change', values.map((id) => map.get(id)).filter(Boolean))
  }
}

async function load(keyword) {
  loading.value = true
  try {
    const params = keyword ? { keyword } : {}
    if (props.includeInactive) params.include_inactive = true
    const data = await personApi.options(Object.keys(params).length ? params : undefined)
    merge(data?.items || [])
  } finally {
    loading.value = false
  }
}

function remoteSearch(keyword) {
  return load(keyword?.trim() || undefined)
}

watch(() => props.preset, () => load(), { deep: false })

onMounted(() => load())
</script>
