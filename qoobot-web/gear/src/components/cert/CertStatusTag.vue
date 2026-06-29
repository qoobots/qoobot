<template>
  <el-tag :type="color" size="small">{{ label }}</el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STATUS_LABELS, STATUS_COLORS } from '@/types/certification'

const props = defineProps<{ status: string }>()

const label = computed(() => STATUS_LABELS[props.status] || props.status)
const color = computed(() => (STATUS_COLORS[props.status] || 'info') as any)
</script>
