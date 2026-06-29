<template>
  <div class="academy-index">
    <div class="page-header">
      <h1>QooBot Academy</h1>
      <p>在线课程、认证考试、学习路径</p>
    </div>

    <div class="course-grid">
      <div v-for="course in courses" :key="course.id" class="page-card course-card" @click="$router.push(`/academy/courses/${course.id}`)">
        <div class="course-cover">{{ levelIcon(course.level) }}</div>
        <div class="course-info">
          <el-tag size="small" :type="levelType(course.level)">{{ course.level }}</el-tag>
          <h3>{{ course.title }}</h3>
          <p>{{ course.description }}</p>
          <div class="course-stats">
            <span>📚 {{ course.lessonCount }} 课时</span>
            <span>👥 {{ course.enrolledCount }} 学员</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { academyApi, type Course } from '@/api/academy'

const courses = ref<Course[]>([])

onMounted(async () => {
  try {
    courses.value = await academyApi.getCourses()
  } catch {}
})

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
.course-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.course-card {
  cursor: pointer;
  transition: transform 0.2s;

  &:hover { transform: translateY(-2px); }

  .course-cover {
    font-size: 48px;
    text-align: center;
    padding: 24px;
  }

  .course-info {
    h3 { font-size: 16px; margin: 8px 0; }
    p { font-size: 13px; color: var(--qoo-text-secondary); line-height: 1.5; }
    .course-stats {
      margin-top: 12px;
      font-size: 12px;
      color: var(--qoo-text-secondary);
      display: flex;
      gap: 16px;
    }
  }
}
</style>
