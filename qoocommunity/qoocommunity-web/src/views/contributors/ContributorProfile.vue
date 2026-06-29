<template>
  <div class="contributor-profile" v-if="contributor">
    <el-breadcrumb style="margin-bottom: 16px">
      <el-breadcrumb-item :to="{ path: '/contributors' }">贡献者</el-breadcrumb-item>
      <el-breadcrumb-item>{{ contributor.nickname }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-card profile-card">
      <div class="profile-avatar">
        <el-avatar :size="80" :src="contributor.avatarUrl">{{ contributor.nickname?.[0] }}</el-avatar>
      </div>
      <div class="profile-info">
        <div class="profile-title">
          <h2>{{ contributor.nickname }}</h2>
          <el-tag size="small" :type="levelType(contributor.level)">{{ contributor.level }}</el-tag>
          <el-tag v-if="contributor.claSigned" size="small" type="success">CLA 已签署</el-tag>
        </div>
        <p class="profile-bio">{{ contributor.bio || '暂无简介' }}</p>
        <p class="profile-joined">加入时间：{{ contributor.joinedAt }}</p>
      </div>
    </div>

    <div class="page-card stats-card" v-if="stats">
      <h3>贡献统计</h3>
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-value">{{ stats.prCount }}</div>
          <div class="stat-label">Pull Request</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ stats.issueCount }}</div>
          <div class="stat-label">Issue</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ stats.commitCount }}</div>
          <div class="stat-label">代码提交</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ stats.reviewCount }}</div>
          <div class="stat-label">Code Review</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { contributorApi, type Contributor, type ContributorStats } from '@/api/contributor'

const route = useRoute()
const contributor = ref<Contributor | null>(null)
const stats = ref<ContributorStats | null>(null)

onMounted(async () => {
  const userId = route.params.id as string
  try {
    contributor.value = await contributorApi.getContributor(userId)
    stats.value = await contributorApi.getContributorStats(userId)
  } catch {}
})

function levelType(level: string) {
  const types: Record<string, string> = { 'BEGINNER': 'success', 'INTERMEDIATE': 'warning', 'ADVANCED': 'danger', 'MAINTAINER': '' }
  return types[level] || 'info'
}
</script>

<style lang="scss" scoped>
.profile-card {
  display: flex;
  gap: 24px;
  align-items: flex-start;

  .profile-avatar {
    flex-shrink: 0;
  }

  .profile-info {
    .profile-title {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;

      h2 { font-size: 20px; }
    }
    .profile-bio {
      font-size: 14px;
      color: var(--qoo-text);
      line-height: 1.6;
      margin-bottom: 8px;
    }
    .profile-joined {
      font-size: 12px;
      color: var(--qoo-text-secondary);
    }
  }
}

.stats-card {
  h3 { font-size: 18px; margin-bottom: 16px; }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-item {
  text-align: center;
  padding: 16px;
  background: var(--qoo-bg);
  border-radius: 8px;

  .stat-value { font-size: 28px; font-weight: 700; color: var(--qoo-primary); }
  .stat-label { font-size: 12px; color: var(--qoo-text-secondary); margin-top: 4px; }
}
</style>
