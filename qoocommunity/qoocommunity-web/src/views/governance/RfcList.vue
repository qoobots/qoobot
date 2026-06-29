<template>
  <div class="rfc-list">
    <div class="page-header">
      <h1>RFC 提案</h1>
      <p>设计提案 → 讨论 → 投票 → 实施</p>
    </div>

    <div class="rfc-list-body">
      <div v-for="rfc in rfcs" :key="rfc.id" class="page-card rfc-card" @click="$router.push(`/governance/rfcs/${rfc.id}`)">
        <div class="rfc-main">
          <h3 class="rfc-title">{{ rfc.title }}</h3>
          <p class="rfc-summary">{{ rfc.summary }}</p>
          <div class="rfc-meta">
            <span>{{ rfc.author }}</span>
            <span>{{ rfc.createdAt }}</span>
            <span v-if="rfc.commentCount">💬 {{ rfc.commentCount }}</span>
          </div>
        </div>
        <div class="rfc-status">
          <el-tag :type="statusType(rfc.status)" size="small">{{ statusText(rfc.status) }}</el-tag>
        </div>
      </div>
    </div>

    <div v-if="rfcs.length === 0" class="page-card empty-state">
      <p>暂无 RFC 提案</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { governanceApi, type Rfc } from '@/api/governance'

const rfcs = ref<Rfc[]>([])

onMounted(async () => {
  try {
    rfcs.value = await governanceApi.getRfcs()
  } catch {}
})

function statusType(status: string) {
  const types: Record<string, string> = { 'PENDING': 'warning', 'DISCUSSION': 'primary', 'APPROVED': 'success', 'IMPLEMENTED': '' }
  return types[status] || 'info'
}

function statusText(status: string): string {
  const texts: Record<string, string> = { 'PENDING': '提案中', 'DISCUSSION': '讨论中', 'APPROVED': '已通过', 'IMPLEMENTED': '已实施' }
  return texts[status] || status
}
</script>

<style lang="scss" scoped>
.rfc-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  cursor: pointer;
  transition: all 0.2s;

  &:hover { border-color: var(--qoo-primary); }

  .rfc-main {
    flex: 1;
    min-width: 0;

    .rfc-title { font-size: 16px; margin-bottom: 8px; }
    .rfc-summary {
      font-size: 13px;
      color: var(--qoo-text-secondary);
      line-height: 1.5;
      margin-bottom: 8px;
    }
    .rfc-meta {
      font-size: 12px;
      color: var(--qoo-text-secondary);
      display: flex;
      gap: 12px;
    }
  }

  .rfc-status {
    flex-shrink: 0;
    margin-left: 16px;
  }
}

.empty-state {
  text-align: center;
  color: var(--qoo-text-secondary);
  padding: 48px;
}
</style>
