<template>
  <div class="teaching-page">
    <div class="page-header">
      <h2>示教记录</h2>
    </div>

    <el-table :data="records" style="width: 100%" v-loading="loading" empty-text="暂无示教记录">
      <el-table-column prop="name" label="名称" min-width="180">
        <template #default="{ row }">
          <div class="record-name">
            <span>{{ row.name }}</span>
            <el-tag v-if="row.is_verified" type="success" size="small">已验证</el-tag>
          </div>
          <div class="record-desc">{{ row.description }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="robot_id" label="机器人" width="150" />
      <el-table-column prop="operator_name" label="示教员" width="120" />
      <el-table-column prop="duration_ms" label="时长" width="100">
        <template #default="{ row }">
          {{ formatDuration(row.duration_ms) }}
        </template>
      </el-table-column>
      <el-table-column prop="frame_count" label="帧数" width="100" />
      <el-table-column prop="quality_score" label="质量评分" width="100">
        <template #default="{ row }">
          <el-rate v-model="row.quality_score" disabled show-score :max="5" size="small" />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="标签" width="200">
        <template #default="{ row }">
          <el-tag v-for="tag in row.tags" :key="tag" size="small" style="margin: 2px">
            {{ tag }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { teachingApi } from '@/api/teleop'
import type { TeachingRecord } from '@/types/teleop'

const records = ref<TeachingRecord[]>([])
const loading = ref(false)

function formatDuration(ms: number): string {
  const s = Math.floor(ms / 1000)
  const m = Math.floor(s / 60)
  const sec = s % 60
  return m > 0 ? `${m}m ${sec}s` : `${sec}s`
}

async function fetchRecords() {
  loading.value = true
  try {
    const { data } = await teachingApi.list()
    if (data.code === 0) records.value = data.data || []
  } catch (e) {
    console.error('Failed to fetch teaching records:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchRecords)
</script>

<style lang="scss" scoped>
.teaching-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;

  h2 { font-size: 20px; font-weight: 600; }
}

.record-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.record-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}
</style>
