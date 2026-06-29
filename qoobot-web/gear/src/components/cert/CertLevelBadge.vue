<template>
  <el-tag :type="color" size="small" effect="plain">{{ label }}</el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CERT_LEVEL_LABELS } from '@/types/certification'

const props = defineProps<{ level: string }>()

const label = computed(() => CERT_LEVEL_LABELS[props.level] || props.level)
const color = computed(() => {
  const colors: Record<string, string> = { basic: '', premium: 'warning', pro: 'danger' }
  return colors[props.level] || ''
})
</script>
