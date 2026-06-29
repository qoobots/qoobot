<template>
  <div class="course-view" v-if="course">
    <el-breadcrumb style="margin-bottom: 16px">
      <el-breadcrumb-item :to="{ path: '/academy' }">学院</el-breadcrumb-item>
      <el-breadcrumb-item>{{ course.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-card">
      <div class="course-cover">{{ levelIcon(course.level) }}</div>
      <div class="course-header">
        <h1>{{ course.title }}</h1>
        <el-tag size="small" :type="levelType(course.level)">{{ course.level }}</el-tag>
      </div>
      <div class="course-stats">
        <span>📚 {{ course.lessonCount }} 课时</span>
        <span>👥 {{ course.enrolledCount }} 学员</span>
        <span>⏱ {{ course.durationMinutes }} 分钟</span>
      </div>
    </div>

    <div class="page-card">
      <MarkdownViewer :content="course.description" />
    </div>

    <div class="page-card enroll-section">
      <el-button type="primary" size="large" @click="enroll">立即报名</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { academyApi, type Course } from '@/api/academy'
import MarkdownViewer from '@/components/common/MarkdownViewer.vue'

const route = useRoute()
const course = ref<Course | null>(null)

onMounted(async () => {
  try {
    course.value = await academyApi.getCourse(Number(route.params.id))
  } catch {}
})

async function enroll() {
  if (!course.value) return
  try {
    await academyApi.enroll(course.value.id)
    ElMessage.success('报名成功！')
  } catch {}
}

function levelIcon(level: string) {
  const icons: Record<string, string> = { 'BEGINNER': '🌱', 'INTERMEDIATE': '🌿', 'ADVANCED': '🌳' }
  return icons[level] || '📚'
}

function levelType(level: string) {
  const types: Record<string, string> = { 'BEGINNER': 'success', 'INTERMEDIATE': 'warning', 'ADVANCED': 'danger' }
  return types[level] || 'info'
}
</script>

<style lang="scss" scoped>
.course-cover {
  font-size: 48px;
  text-align: center;
  padding: 24px;
}

.course-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;

  h1 { font-size: 24px; }
}

.course-stats {
  display: flex;
  gap: 24px;
  font-size: 14px;
  color: var(--qoo-text-secondary);
}

.enroll-section {
  text-align: center;
}
</style>
