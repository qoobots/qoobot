<template>
  <div class="contributor-wall">
    <div class="page-header">
      <h1>贡献者墙</h1>
      <p>感谢每一位为 QooBot 生态做出贡献的开发者</p>
    </div>

    <div class="contributor-grid">
      <div v-for="contributor in contributors" :key="contributor.userId" class="page-card contributor-card" @click="$router.push(`/contributors/${contributor.userId}`)">
        <div class="contributor-avatar">
          <el-avatar :size="64" :src="contributor.avatarUrl">{{ contributor.nickname?.[0] }}</el-avatar>
        </div>
        <div class="contributor-info">
          <h3>{{ contributor.nickname }}</h3>
          <el-tag size="small" :type="levelType(contributor.level)">{{ contributor.level }}</el-tag>
          <div class="contributor-stats">
            <span>📦 {{ contributor.contributeCount || contributor.prCount }} 贡献</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="contributors.length === 0" class="page-card empty-state">
      <p>暂无贡献者数据</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { contributorApi, type Contributor } from '@/api/contributor'

const contributors = ref<Contributor[]>([])

onMounted(async () => {
  try {
    contributors.value = await contributorApi.getContributorWall()
  } catch {}
})

function levelType(level: string) {
  const types: Record<string, string> = { 'BEGINNER': 'success', 'INTERMEDIATE': 'warning', 'ADVANCED': 'danger', 'MAINTAINER': '' }
  return types[level] || 'info'
}
</script>

<style lang="scss" scoped>
.contributor-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.contributor-card {
  cursor: pointer;
  text-align: center;
  transition: transform 0.2s;

  &:hover { transform: translateY(-2px); }

  .contributor-avatar {
    margin-bottom: 12px;
  }

  .contributor-info {
    h3 { font-size: 14px; margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .contributor-stats {
      margin-top: 8px;
      font-size: 12px;
      color: var(--qoo-text-secondary);
    }
  }
}

.empty-state {
  text-align: center;
  color: var(--qoo-text-secondary);
  padding: 48px;
}
</style>
