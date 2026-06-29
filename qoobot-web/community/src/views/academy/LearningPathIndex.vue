<template>
  <div class="learning-path-index">
    <div class="page-header">
      <h1>学习路径</h1>
      <p>从零基础到机器人专家，跟随结构化学习路径循序渐进</p>
    </div>

    <div class="level-filters">
      <el-radio-group v-model="filter" size="default">
        <el-radio-button value="ALL">全部</el-radio-button>
        <el-radio-button value="BEGINNER">入门</el-radio-button>
        <el-radio-button value="INTERMEDIATE">中级</el-radio-button>
        <el-radio-button value="ADVANCED">高级</el-radio-button>
      </el-radio-group>
    </div>

    <div v-if="!loading && filteredPaths.length === 0" class="page-card empty-state">
      <el-empty description="暂无学习路径" />
    </div>

    <div v-else class="path-grid">
      <div v-for="path in filteredPaths" :key="path.id" class="page-card path-card"
        @click="$router.push(`/academy/learning-paths/${path.slug}`)">
        <div class="path-cover" :style="{ background: coverGradient(path.level) }">
          <el-tag :type="levelTagType(path.level)" size="small" class="level-badge">
            {{ levelLabel(path.level) }}
          </el-tag>
        </div>
        <div class="path-info">
          <h3>{{ path.title }}</h3>
          <p class="path-desc">{{ path.description }}</p>
          <div class="path-meta">
            <span class="course-count">{{ path.courseCount || 0 }} 门课程</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { academyApi, type LearningPath } from '@/api/academy'

const paths = ref<LearningPath[]>([])
const filter = ref('ALL')
const loading = ref(true)

const filteredPaths = computed(() =>
  filter.value === 'ALL'
    ? paths.value
    : paths.value.filter(p => p.level === filter.value)
)

const levelLabel = (l: string) =>
  ({ BEGINNER: '入门', INTERMEDIATE: '中级', ADVANCED: '高级' } as Record<string, string>)[l] || l

const levelTagType = (l: string) =>
  ({ BEGINNER: 'success', INTERMEDIATE: 'warning', ADVANCED: 'danger' } as Record<string, string>)[l] || 'info'

const coverGradient = (level: string) => {
  const g: Record<string, string> = {
    BEGINNER: 'linear-gradient(135deg, #43e97b, #38f9d7)',
    INTERMEDIATE: 'linear-gradient(135deg, #4facfe, #00f2fe)',
    ADVANCED: 'linear-gradient(135deg, #667eea, #764ba2)'
  }
  return g[level] || 'linear-gradient(135deg, #4A90D9, #34C759)'
}

onMounted(async () => {
  try {
    paths.value = await academyApi.getLearningPaths()
  } catch { } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.level-filters {
  margin-bottom: 24px;
}

.path-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.path-card {
  cursor: pointer;
  overflow: hidden;
  padding: 0;
  transition: transform 0.2s;

  &:hover {
    transform: translateY(-2px);
  }

  .path-cover {
    height: 100px;
    display: flex;
    align-items: flex-start;
    justify-content: flex-end;
    padding: 12px;
  }

  .level-badge {
    font-weight: 600;
  }

  .path-info {
    padding: 16px;

    h3 {
      font-size: 16px;
      margin-bottom: 8px;
    }

    .path-desc {
      font-size: 13px;
      color: var(--qoo-text-secondary);
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .path-meta {
      margin-top: 12px;
      font-size: 12px;
      color: var(--qoo-text-secondary);

      .course-count {
        background: var(--el-fill-color-light);
        padding: 2px 8px;
        border-radius: 4px;
      }
    }
  }
}
</style>
