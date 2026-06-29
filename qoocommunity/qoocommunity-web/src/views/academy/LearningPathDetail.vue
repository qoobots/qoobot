<template>
  <div class="learning-path-detail">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item :to="{ path: '/academy' }">学院</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: '/academy/learning-paths' }">学习路径</el-breadcrumb-item>
      <el-breadcrumb-item>{{ path?.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div v-if="path" class="path-hero page-card" :style="{ borderTop: `4px solid ${levelColor(path.level)}` }">
      <div class="hero-info">
        <el-tag :type="levelTagType(path.level)" size="small">{{ levelLabel(path.level) }}</el-tag>
        <h1>{{ path.title }}</h1>
        <p class="hero-desc">{{ path.description }}</p>
        <div class="hero-meta">
          <span>{{ path.courseCount || 0 }} 门课程</span>
        </div>
      </div>
    </div>

    <div v-if="path" class="path-courses">
      <h2>课程列表</h2>
      <div v-if="path.courseCount === 0" class="page-card empty-state">
        <el-empty description="此学习路径暂无课程" />
      </div>
      <div v-else class="page-card course-placeholder">
        <el-result icon="success" title="学习路径已就绪" sub-title="课程内容正在整理中，敬请期待">
          <template #extra>
            <el-button type="primary" @click="$router.push('/academy')">浏览所有课程</el-button>
          </template>
        </el-result>
      </div>
    </div>

    <div v-else-if="!loading" class="page-card empty-state">
      <el-empty description="学习路径不存在" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { academyApi, type LearningPath } from '@/api/academy'

const route = useRoute()
const path = ref<LearningPath | null>(null)
const loading = ref(true)

const levelLabel = (l: string) =>
  ({ BEGINNER: '入门', INTERMEDIATE: '中级', ADVANCED: '高级' } as Record<string, string>)[l] || l

const levelTagType = (l: string) =>
  ({ BEGINNER: 'success', INTERMEDIATE: 'warning', ADVANCED: 'danger' } as Record<string, string>)[l] || 'info'

const levelColor = (l: string) => {
  const c: Record<string, string> = {
    BEGINNER: '#43e97b',
    INTERMEDIATE: '#4facfe',
    ADVANCED: '#667eea'
  }
  return c[l] || '#4A90D9'
}

onMounted(async () => {
  try {
    path.value = await academyApi.getLearningPath(route.params.slug as string)
  } catch { } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.el-breadcrumb {
  margin-bottom: 16px;
}

.path-hero {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;

  .hero-info {
    h1 {
      font-size: 24px;
      margin: 12px 0 8px;
    }

    .hero-desc {
      font-size: 14px;
      color: var(--qoo-text-secondary);
      line-height: 1.6;
    }

    .hero-meta {
      margin-top: 12px;
      font-size: 13px;
      color: var(--qoo-text-secondary);
    }
  }
}

.path-courses h2 {
  font-size: 18px;
  margin-bottom: 16px;
}
</style>
