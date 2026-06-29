<template>
  <div class="cert-detail" v-if="cert">
    <el-breadcrumb style="margin-bottom: 16px">
      <el-breadcrumb-item :to="{ path: '/academy/cert' }">认证中心</el-breadcrumb-item>
      <el-breadcrumb-item>{{ cert.name }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-card">
      <div class="cert-icon">{{ levelIcon(cert.level) }}</div>
      <h1>{{ cert.name }}</h1>
      <el-tag size="small" :type="levelType(cert.level)">{{ cert.level }}</el-tag>
      <p class="cert-desc">{{ cert.description }}</p>
      <div class="cert-meta">
        <span>⏱ 考试时长：{{ cert.examDuration }} 分钟</span>
        <span>📝 题目数量：{{ cert.questionCount }} 题</span>
        <span>✅ 通过分数：{{ cert.passScore }} 分</span>
      </div>
    </div>

    <div class="page-card">
      <el-button type="primary" size="large" @click="startExam">开始考试</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { academyApi, type Certification } from '@/api/academy'

const route = useRoute()
const cert = ref<Certification | null>(null)

onMounted(async () => {
  try {
    cert.value = await academyApi.getCertification(Number(route.params.id))
  } catch {}
})

async function startExam() {
  if (!cert.value) return
  try {
    await academyApi.submitExam(cert.value.id, {})
    ElMessage.success('考试已提交！')
  } catch {}
}

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
.cert-icon {
  font-size: 64px;
  text-align: center;
  padding: 24px;
}

h1 {
  font-size: 24px;
  text-align: center;
  margin: 16px 0;
}

.cert-desc {
  font-size: 14px;
  color: var(--qoo-text-secondary);
  line-height: 1.6;
  text-align: center;
  margin: 16px 0;
}

.cert-meta {
  display: flex;
  justify-content: center;
  gap: 24px;
  font-size: 13px;
  color: var(--qoo-text-secondary);
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--qoo-border);
}
</style>
