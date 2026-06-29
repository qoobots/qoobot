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
      <el-button v-if="!enrolled" type="primary" size="large" @click="enroll">立即报名</el-button>
      <el-button v-else-if="lessons.length" type="primary" size="large" @click="$router.push(`/academy/courses/${course.id}/lessons/${lessons[0].id}`)">
        开始学习
      </el-button>
      <el-button v-else type="primary" size="large" @click="enroll">开始学习</el-button>
    </div>

    <div class="page-header" style="margin-top: 24px">
      <h2>课程目录</h2>
      <p>共 {{ lessons.length }} 个课时</p>
    </div>

    <el-skeleton :loading="lessonsLoading" animated :count="3">
      <template #template>
        <div v-for="i in 3" :key="i" class="page-card">
          <el-skeleton-item variant="text" style="width: 50%;" />
          <el-skeleton-item variant="text" style="width: 100%;" />
        </div>
      </template>

      <template #default>
        <div v-if="lessons.length" class="lessons-list">
          <div
            v-for="(item, idx) in lessons"
            :key="item.id"
            class="page-card lesson-card"
            @click="$router.push(`/academy/courses/${course.id}/lessons/${item.id}`)"
          >
            <div class="lesson-index">{{ idx + 1 }}</div>
            <div class="lesson-body">
              <div class="lesson-title-row">
                <h4>{{ item.title }}</h4>
                <el-tag v-if="isLessonCompleted(item.id)" type="success" size="small">✓ 已完成</el-tag>
              </div>
              <p v-if="item.description" class="lesson-desc">{{ item.description }}</p>
              <div class="lesson-meta">
                <span v-if="item.duration">⏱ {{ item.duration }} 分钟</span>
              </div>
            </div>
            <div class="lesson-arrow">→</div>
          </div>
        </div>
        <el-empty v-else description="暂无课时" />
      </template>
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { academyApi, type Course, type Lesson } from '@/api/academy'
import MarkdownViewer from '@/components/common/MarkdownViewer.vue'

const route = useRoute()
const course = ref<Course | null>(null)
const lessons = ref<Lesson[]>([])
const enrolled = ref(false)
const lessonsLoading = ref(true)
const completedLessonIds = ref<Set<number>>(new Set())

onMounted(async () => {
  try {
    const courseId = Number(route.params.id)
    course.value = await academyApi.getCourse(courseId)

    // Load lessons
    try {
      lessons.value = await academyApi.getLessons(courseId)
    } catch {}

    // Check enrollment and progress
    try {
      const myCourses = await academyApi.getMyCourses()
      const mc = Array.isArray(myCourses) ? myCourses : []
      enrolled.value = mc.some((c: any) => c.id === courseId || c.courseId === courseId)
    } catch {}

    try {
      const progress = await academyApi.getMyProgress()
      const lp = Array.isArray(progress) ? progress : []
      completedLessonIds.value = new Set(lp.filter((p: any) => p.isCompleted).map((p: any) => p.lessonId))
    } catch {}
  } catch {} finally {
    lessonsLoading.value = false
  }
})

function isLessonCompleted(lessonId: number): boolean {
  return completedLessonIds.value.has(lessonId)
}

async function enroll() {
  if (!course.value) return
  try {
    await academyApi.enroll(course.value.id)
    enrolled.value = true
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

.lessons-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.lesson-card {
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 1px;
  border-radius: 0;

  &:first-child { border-radius: 12px 12px 0 0; }
  &:last-child { border-radius: 0 0 12px 12px; }
  &:only-child { border-radius: 12px; }

  &:hover { background: var(--qoo-bg); }
}

.lesson-index {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--qoo-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--qoo-text-secondary);
  flex-shrink: 0;
}

.lesson-body {
  flex: 1;
  min-width: 0;

  .lesson-title-row {
    display: flex;
    align-items: center;
    gap: 8px;

    h4 { font-size: 15px; }
  }

  .lesson-desc {
    font-size: 13px;
    color: var(--qoo-text-secondary);
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .lesson-meta {
    margin-top: 4px;
    font-size: 12px;
    color: var(--qoo-text-secondary);
  }
}

.lesson-arrow {
  font-size: 18px;
  color: var(--qoo-text-secondary);
  flex-shrink: 0;
}
</style>
