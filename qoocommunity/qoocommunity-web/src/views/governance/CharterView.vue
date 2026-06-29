<template>
  <div class="charter-view">
    <div class="page-header">
      <h1>社区宪章</h1>
      <p>行为准则、社区价值观、争议解决机制</p>
    </div>

    <div class="page-card charter-content" v-if="charter">
      <div class="charter-meta">
        <span v-if="charter.version">版本：{{ charter.version }}</span>
        <span v-if="charter.adoptedAt">通过时间：{{ charter.adoptedAt }}</span>
        <span v-if="charter.updatedAt">更新于：{{ charter.updatedAt }}</span>
      </div>
      <MarkdownViewer :content="charter.content" />
    </div>

    <div v-else class="page-card empty-state">
      <p>暂无宪章内容</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { governanceApi, type Charter } from '@/api/governance'
import MarkdownViewer from '@/components/common/MarkdownViewer.vue'

const charter = ref<Charter | null>(null)

onMounted(async () => {
  try {
    charter.value = await governanceApi.getCharter()
  } catch {}
})
</script>

<style lang="scss" scoped>
.charter-content {
  min-height: 200px;
}

.charter-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--qoo-text-secondary);
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--qoo-border);
}

.empty-state {
  text-align: center;
  color: var(--qoo-text-secondary);
  padding: 48px;
}
</style>
