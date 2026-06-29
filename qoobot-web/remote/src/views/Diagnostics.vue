<template>
  <div class="diagnostics-page">
    <div class="page-header">
      <h2>远程诊断</h2>
      <el-select v-model="severityFilter" placeholder="严重级别" clearable style="width: 140px">
        <el-option label="全部" value="" />
        <el-option label="INFO" value="INFO" />
        <el-option label="WARNING" value="WARNING" />
        <el-option label="ERROR" value="ERROR" />
        <el-option label="CRITICAL" value="CRITICAL" />
        <el-option label="FATAL" value="FATAL" />
      </el-select>
    </div>

    <el-timeline v-if="events.length" v-loading="loading">
      <el-timeline-item
        v-for="event in filteredEvents"
        :key="event.timestamp_ns"
        :timestamp="new Date(event.timestamp_ns / 1000000).toLocaleString()"
        :type="severityColor(event.severity)"
        :color="severityColor(event.severity)"
        placement="top"
      >
        <el-card shadow="hover">
          <div class="event-header">
            <el-tag :type="severityTagType(event.severity)" size="small">
              {{ event.severity }}
            </el-tag>
            <span class="event-component">{{ event.component }}</span>
          </div>
          <div class="event-message">{{ event.message }}</div>
          <div v-if="event.detail" class="event-detail">{{ event.detail }}</div>
        </el-card>
      </el-timeline-item>
    </el-timeline>

    <el-empty v-else-if="!loading" description="暂无诊断事件" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { diagnosticsApi } from '@/api/teleop'
import type { DiagnosticEvent } from '@/types/teleop'

const events = ref<DiagnosticEvent[]>([])
const loading = ref(false)
const severityFilter = ref('')

const filteredEvents = computed(() =>
  severityFilter.value
    ? events.value.filter(e => e.severity === severityFilter.value)
    : events.value
)

function severityColor(severity: string): string {
  const map: Record<string, string> = {
    INFO: '#409eff', WARNING: '#e6a23c', ERROR: '#f56c6c',
    CRITICAL: '#f56c6c', FATAL: '#ff0000'
  }
  return map[severity] || '#909399'
}

function severityTagType(severity: string): string {
  const map: Record<string, string> = {
    INFO: '', WARNING: 'warning', ERROR: 'danger',
    CRITICAL: 'danger', FATAL: 'danger'
  }
  return map[severity] || 'info'
}

async function fetchEvents() {
  loading.value = true
  try {
    const { data } = await diagnosticsApi.events({ limit: 50 })
    if (data.code === 0) events.value = data.data || []
  } catch (e) {
    console.error('Failed to fetch diagnostics:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchEvents)
</script>

<style lang="scss" scoped>
.diagnostics-page {
  padding: 24px;
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;

  h2 { font-size: 20px; font-weight: 600; }
}

.event-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.event-component {
  font-weight: 500;
  font-size: 13px;
}

.event-message {
  font-size: 13px;
  color: var(--el-text-color-primary);
  margin-bottom: 4px;
}

.event-detail {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  background: var(--el-fill-color-light);
  padding: 4px 8px;
  border-radius: 4px;
}
</style>
