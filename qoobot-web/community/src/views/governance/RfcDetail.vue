<template>
  <div class="rfc-detail" v-if="rfc">
    <el-breadcrumb style="margin-bottom: 16px">
      <el-breadcrumb-item :to="{ path: '/governance/rfcs' }">RFC 提案</el-breadcrumb-item>
      <el-breadcrumb-item>{{ rfc.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-card rfc-header">
      <div class="rfc-title-row">
        <h1>{{ rfc.title }}</h1>
        <el-tag :type="statusType(rfc.status)" size="small">{{ statusText(rfc.status) }}</el-tag>
      </div>
      <div class="rfc-meta">
        <span>{{ rfc.author }}</span>
        <span>{{ rfc.createdAt }}</span>
        <span>更新于 {{ rfc.updatedAt }}</span>
      </div>
    </div>

    <div class="page-card rfc-content" v-if="rfc.summary">
      <h3>摘要</h3>
      <p>{{ rfc.summary }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { governanceApi, type Rfc } from '@/api/governance'

const route = useRoute()
const rfc = ref<Rfc | null>(null)

onMounted(async () => {
  try {
    rfc.value = await governanceApi.getRfc(Number(route.params.id))
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
.rfc-header {
  .rfc-title-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;

    h1 { font-size: 24px; }
  }
  .rfc-meta {
    font-size: 13px;
    color: var(--qoo-text-secondary);
    display: flex;
    gap: 16px;
  }
}

.rfc-content {
  h3 { font-size: 16px; margin-bottom: 12px; }
  p {
    font-size: 14px;
    color: var(--qoo-text);
    line-height: 1.8;
  }
}
</style>
