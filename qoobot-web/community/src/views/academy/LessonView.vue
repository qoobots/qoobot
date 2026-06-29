<template>
  <div class="lesson-view">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ path: '/academy' }">学院</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: `/academy/courses/${courseId}` }">{{ course?.title }}</el-breadcrumb-item>
      <el-breadcrumb-item>{{ lesson?.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div v-if="lesson" class="lesson-layout">
      <div class="lesson-main">
        <div class="page-card lesson-content">
          <h2>{{ lesson.title }}</h2>
          <div class="lesson-meta">
            <span v-if="lesson.duration">⏱ {{ lesson.duration }} 分钟</span>
            <el-tag v-if="isCompleted" type="success" size="small">已完成</el-tag>
          </div>

          <div v-if="lesson.videoUrl" class="video-placeholder">
            <div class="video-inner">
              <el-icon :size="48"><VideoPlay /></el-icon>
              <p>视频内容</p>
            </div>
          </div>

          <div class="lesson-body">
            <MarkdownViewer v-if="lesson.contentHtml" :content="lesson.contentHtml" />
            <p v-else>{{ lesson.description }}</p>
          </div>
        </div>

        <div class="lesson-nav">
          <el-button v-if="prevLesson" @click="goPrev" :icon="'ArrowLeft'">上一课</el-button>
          <el-button v-if="nextLesson" type="primary" @click="goNext" :icon="'ArrowRight'" style="margin-left: auto">
            下一课
          </el-button>
          <el-button v-else type="primary" @click="$router.push(`/academy/courses/${courseId}`)" style="margin-left: auto">
            返回课程
          </el-button>
        </div>
      </div>

      <div class="lesson-sidebar">
        <div class="page-card">
          <h3>课时列表</h3>
          <div v-for="(l, idx) in lessons" :key="l.id" class="lesson-item"
            :class="{ active: l.id === lesson.id, completed: false }"
            @click="l.id !== lesson.id && $router.push(`/academy/courses/${courseId}/lessons/${l.id}`)">
            <span class="lesson-num">{{ idx + 1 }}</span>
            <span class="lesson-title">{{ l.title }}</span>
            <span class="lesson-dur" v-if="l.duration">{{ l.duration }}min</span>
          </div>
        </div>

        <div class="page-card mark-section">
          <el-button v-if="!isCompleted" type="success" @click="handleComplete" :loading="completing">
            标记完成
          </el-button>
          <el-tag v-else type="success" size="default">
            ✅ 已完成
          </el-tag>
        </div>
      </div>
    </div>

    <div v-else-if="!loading" class="page-card empty-state">
      <el-empty description="课时不存在" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VideoPlay } from '@element-plus/icons-vue'
import { academyApi, type Lesson, type Course } from '@/api/academy'
import MarkdownViewer from '@/components/common/MarkdownViewer.vue'

const route = useRoute()
const router = useRouter()
const courseId = Number(route.params.courseId)
const lessonId = Number(route.params.lessonId)

const lesson = ref<Lesson | null>(null)
const lessons = ref<Lesson[]>([])
const course = ref<Course | null>(null)
const isCompleted = ref(false)
const completing = ref(false)
const loading = ref(true)

const currentIndex = computed(() => lessons.value.findIndex(l => l.id === lessonId))
const prevLesson = computed(() => currentIndex.value > 0 ? lessons.value[currentIndex.value - 1] : null)
const nextLesson = computed(() => currentIndex.value < lessons.value.length - 1 ? lessons.value[currentIndex.value + 1] : null)

const handleComplete = async () => {
  completing.value = true
  try {
    await academyApi.markLessonComplete(lessonId)
    isCompleted.value = true
  } catch { } finally {
    completing.value = false
  }
}

const goPrev = () => {
  if (prevLesson.value) {
    router.push(`/academy/courses/${courseId}/lessons/${prevLesson.value.id}`)
  }
}

const goNext = () => {
  if (nextLesson.value) {
    router.push(`/academy/courses/${courseId}/lessons/${nextLesson.value.id}`)
  }
}

onMounted(async () => {
  try {
    const [courseData, lessonsData, lessonData] = await Promise.all([
      academyApi.getCourse(courseId),
      academyApi.getLessons(courseId),
      academyApi.getLesson(courseId, lessonId)
    ])
    course.value = courseData
    lessons.value = lessonsData || []
    lesson.value = lessonData
  } catch { } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.el-breadcrumb {
  margin-bottom: 16px;
}

.lesson-layout {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
  align-items: start;
}

.lesson-main {
  .lesson-content {
    h2 { font-size: 22px; margin-bottom: 12px; }

    .lesson-meta {
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 16px;
      font-size: 13px;
      color: var(--qoo-text-secondary);
    }

    .video-placeholder {
      background: linear-gradient(135deg, #1a1a2e, #16213e);
      border-radius: 8px;
      height: 240px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 20px;

      .video-inner {
        text-align: center;
        color: rgba(255, 255, 255, 0.6);

        p { margin-top: 12px; font-size: 14px; }
      }
    }

    .lesson-body {
      font-size: 15px;
      line-height: 1.8;
      color: var(--qoo-text-primary);
    }
  }

  .lesson-nav {
    display: flex;
    justify-content: space-between;
    margin-top: 16px;
  }
}

.lesson-sidebar {
  .page-card {
    margin-bottom: 16px;

    h3 { font-size: 15px; margin-bottom: 12px; }
  }

  .lesson-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    transition: background 0.15s;

    &:hover { background: var(--el-fill-color-light); }

    &.active {
      background: var(--el-color-primary-light-9);
      color: var(--el-color-primary);
    }

    .lesson-num {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: var(--el-fill-color);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      flex-shrink: 0;
    }

    .lesson-title {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .lesson-dur {
      font-size: 11px;
      color: var(--qoo-text-secondary);
    }
  }
}

.mark-section {
  text-align: center;
}
</style>
