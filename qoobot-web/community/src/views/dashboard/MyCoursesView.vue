<template>
  <div class="my-courses">
    <div class="page-header">
      <h1>我的课程</h1>
    </div>

    <div class="course-grid" v-if="courses.length > 0">
      <div v-for="course in courses" :key="course.id" class="page-card course-card" @click="$router.push(`/academy/courses/${course.id}`)">
        <div class="course-cover">{{ levelIcon(course.level) }}</div>
        <div class="course-info">
          <el-tag size="small" :type="levelType(course.level)">{{ course.level }}</el-tag>
          <h3>{{ course.title }}</h3>
          <div class="progress-bar">
            <el-progress :percentage="getProgress(course.id)" :stroke-width="8" />
          </div>
          <div class="course-stats">
            <span>📚 {{ course.lessonCount }} 课时</span>
            <span>⏱ {{ course.durationMinutes }} 分钟</span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="page-card empty-state">
      <p>暂未报名任何课程</p>
      <el-button type="primary" @click="$router.push('/academy')">浏览课程</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { academyApi, type Course } from '@/api/academy'

const courses = ref<Course[]>([])

onMounted(async () => {
  try {
    courses.value = await academyApi.getMyCourses()
  } catch {}
})

function getProgress(courseId: number): number {
  return 0
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
    .progress-bar { margin: 12px 0; }
    .course-stats {
      font-size: 12px;
      color: var(--qoo-text-secondary);
      display: flex;
      gap: 16px;
    }
  }
}

.empty-state {
  text-align: center;
  padding: 48px;

  p {
    color: var(--qoo-text-secondary);
    font-size: 14px;
    margin-bottom: 16px;
  }
}
</style>
