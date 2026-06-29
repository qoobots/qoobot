<template>
  <div class="profile-view">
    <div class="page-header">
      <h1>个人资料</h1>
    </div>

    <div class="page-card profile-card" v-if="profile">
      <div class="profile-avatar">
        <el-avatar :size="80" :src="profile.avatarUrl">{{ profile.nickname?.[0] }}</el-avatar>
      </div>
      <div class="profile-info">
        <h2>{{ profile.nickname }}</h2>
        <p class="profile-email">{{ profile.email }}</p>
        <p class="profile-bio">{{ profile.bio || '这个人很懒，什么都没写~' }}</p>
        <p class="profile-registered">注册时间：{{ profile.registeredAt }}</p>
      </div>
    </div>

    <div class="page-card certs-card">
      <h3>我的证书</h3>
      <div class="my-certs-grid" v-if="myCerts.length > 0">
        <div v-for="cert in myCerts" :key="cert.id" class="cert-item">
          <span class="cert-icon">{{ levelIcon(cert.level) }}</span>
          <div>
            <div class="cert-name">{{ cert.name }}</div>
            <el-tag size="small" :type="levelType(cert.level)">{{ cert.level }}</el-tag>
          </div>
        </div>
      </div>
      <p v-else class="empty-text">暂无认证证书</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { userApi, type UserProfile } from '@/api/user'
import { academyApi, type Certification } from '@/api/academy'

const profile = ref<UserProfile | null>(null)
const myCerts = ref<Certification[]>([])

onMounted(async () => {
  try {
    profile.value = await userApi.getProfile()
    myCerts.value = await academyApi.getMyCerts()
  } catch {}
})

function levelIcon(level: string) {
  const icons: Record<string, string> = { 'BEGINNER': '🥉', 'INTERMEDIATE': '🥈', 'ADVANCED': '🥇' }
  return icons[level] || '📜'
}

function levelType(level: string) {
  const types: Record<string, string> = { 'BEGINNER': 'success', 'INTERMEDIATE': 'warning', 'ADVANCED': 'danger' }
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
    h2 { font-size: 20px; margin-bottom: 8px; }
    .profile-email { font-size: 14px; color: var(--qoo-text-secondary); margin-bottom: 8px; }
    .profile-bio { font-size: 14px; color: var(--qoo-text); line-height: 1.6; margin-bottom: 8px; }
    .profile-registered { font-size: 12px; color: var(--qoo-text-secondary); }
  }
}

.certs-card {
  h3 { font-size: 18px; margin-bottom: 16px; }
}

.my-certs-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.cert-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--qoo-bg);
  border-radius: 8px;

  .cert-icon { font-size: 24px; }
  .cert-name { font-size: 14px; font-weight: 500; margin-bottom: 4px; }
}

.empty-text {
  color: var(--qoo-text-secondary);
  font-size: 14px;
  text-align: center;
  padding: 24px;
}
</style>
