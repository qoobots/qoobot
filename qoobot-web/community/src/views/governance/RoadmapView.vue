<template>
  <div class="roadmap-view">
    <div class="page-header">
      <h1>路线图</h1>
      <p>公开路线图，社区投票决定优先级</p>
    </div>

    <el-timeline v-if="roadmap.length > 0">
      <el-timeline-item
        v-for="item in roadmap"
        :key="item.version"
        :timestamp="item.targetDate"
        placement="top"
        :color="statusColor(item.status)"
      >
        <div class="page-card roadmap-item">
          <div class="roadmap-header">
            <h3>{{ item.version }} - {{ item.title }}</h3>
            <el-tag :type="statusType(item.status)" size="small">{{ statusText(item.status) }}</el-tag>
          </div>
          <p class="roadmap-desc">{{ item.description }}</p>
          <ul class="roadmap-features" v-if="item.features && item.features.length > 0">
            <li v-for="feature in item.features" :key="feature">{{ feature }}</li>
          </ul>
        </div>
      </el-timeline-item>
    </el-timeline>

    <div v-else class="page-card empty-state">
      <p>暂无路线图信息</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { governanceApi, type RoadmapItem } from '@/api/governance'

const roadmap = ref<RoadmapItem[]>([])

onMounted(async () => {
  try {
    roadmap.value = await governanceApi.getRoadmap()
  } catch {}
})

function statusColor(status: string): string {
  const colors: Record<string, string> = { 'COMPLETED': '#34C759', 'IN_PROGRESS': '#4A90D9', 'PLANNED': '#E5E7EB' }
  return colors[status] || '#E5E7EB'
}

function statusType(status: string) {
  const types: Record<string, string> = { 'COMPLETED': 'success', 'IN_PROGRESS': 'primary', 'PLANNED': 'info' }
  return types[status] || 'info'
}

function statusText(status: string): string {
  const texts: Record<string, string> = { 'COMPLETED': '已完成', 'IN_PROGRESS': '进行中', 'PLANNED': '计划中' }
  return texts[status] || status
}
</script>

<style lang="scss" scoped>
.roadmap-item {
  .roadmap-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;

    h3 { font-size: 16px; }
  }

  .roadmap-desc {
    font-size: 14px;
    color: var(--qoo-text-secondary);
    line-height: 1.6;
    margin-bottom: 12px;
  }

  .roadmap-features {
    padding-left: 20px;

    li {
      font-size: 13px;
      color: var(--qoo-text);
      line-height: 1.8;
    }
  }
}

.empty-state {
  text-align: center;
  color: var(--qoo-text-secondary);
  padding: 48px;
}
</style>
