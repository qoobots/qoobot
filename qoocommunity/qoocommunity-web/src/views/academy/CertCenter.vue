<template>
  <div class="cert-center">
    <div class="page-header">
      <h1>认证中心</h1>
      <p>QooBot 开发者认证（初级/高级/专家）</p>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="全部认证" name="all" />
      <el-tab-pane label="我的证书" name="mine" />
    </el-tabs>

    <div class="cert-grid">
      <div v-for="cert in filteredCerts" :key="cert.id" class="page-card cert-card" @click="$router.push(`/academy/cert/${cert.id}`)">
        <div class="cert-icon">{{ levelIcon(cert.level) }}</div>
        <div class="cert-info">
          <el-tag size="small" :type="levelType(cert.level)">{{ cert.level }}</el-tag>
          <h3>{{ cert.name }}</h3>
          <p>{{ cert.description }}</p>
          <div class="cert-stats">
            <span>⏱ {{ cert.examDuration }} 分钟</span>
            <span>📝 {{ cert.questionCount }} 题</span>
            <span>✅ {{ cert.passScore }} 分通过</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="filteredCerts.length === 0" class="page-card empty-state">
      <p>暂无认证记录</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { academyApi, type Certification } from '@/api/academy'

const certs = ref<Certification[]>([])
const myCerts = ref<Certification[]>([])
const activeTab = ref('all')

onMounted(async () => {
  try {
    certs.value = await academyApi.getCertifications()
    myCerts.value = await academyApi.getMyCerts()
  } catch {}
})

const filteredCerts = computed(() => {
  return activeTab.value === 'mine' ? myCerts.value : certs.value
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
.cert-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.cert-card {
  cursor: pointer;
  transition: transform 0.2s;

  &:hover { transform: translateY(-2px); }

  .cert-icon {
    font-size: 48px;
    text-align: center;
    padding: 24px;
  }

  .cert-info {
    h3 { font-size: 16px; margin: 8px 0; }
    p { font-size: 13px; color: var(--qoo-text-secondary); line-height: 1.5; }
    .cert-stats {
      margin-top: 12px;
      font-size: 12px;
      color: var(--qoo-text-secondary);
      display: flex;
      gap: 16px;
    }
  }
}

.empty-state {
  text-align: center;
  color: var(--qoo-text-secondary);
  padding: 48px;
}
</style>
