<template>
  <div class="showcase-detail" v-if="showcase">
    <el-breadcrumb style="margin-bottom: 16px">
      <el-breadcrumb-item :to="{ path: '/showcase' }">案例展示</el-breadcrumb-item>
      <el-breadcrumb-item>{{ showcase.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-card">
      <div class="showcase-cover" :style="{ background: gradientFor(showcase.category) }">
        <span class="showcase-category">{{ showcase.category }}</span>
      </div>
      <div class="showcase-info">
        <h1>{{ showcase.title }}</h1>
        <div class="showcase-meta">
          <span>{{ showcase.author }}</span>
          <span>{{ showcase.createdAt }}</span>
        </div>
        <p class="showcase-desc">{{ showcase.description }}</p>
        <el-button v-if="showcase.url" type="primary" @click="openUrl">访问项目</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { contentApi, type Showcase } from '@/api/content'

const route = useRoute()
const showcase = ref<Showcase | null>(null)

onMounted(async () => {
  try {
    showcase.value = await contentApi.getShowcase(Number(route.params.id))
  } catch {}
})

function openUrl() {
  if (showcase.value?.url) {
    window.open(showcase.value.url, '_blank')
  }
}

function gradientFor(category: string): string {
  const gradients: Record<string, string> = {
    '机器人': 'linear-gradient(135deg, #667eea, #764ba2)',
    '智能制造': 'linear-gradient(135deg, #f093fb, #f5576c)',
    '科研教育': 'linear-gradient(135deg, #4facfe, #00f2fe)',
    '创客': 'linear-gradient(135deg, #43e97b, #38f9d7)',
    '其他': 'linear-gradient(135deg, #fa709a, #fee140)'
  }
  return gradients[category] || 'linear-gradient(135deg, #4A90D9, #34C759)'
}
</script>

<style lang="scss" scoped>
.showcase-cover {
  height: 160px;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 24px;

  .showcase-category {
    background: rgba(255,255,255,0.25);
    color: #fff;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }
}

.showcase-info {
  h1 { font-size: 24px; margin-bottom: 12px; }
  .showcase-meta {
    font-size: 13px;
    color: var(--qoo-text-secondary);
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
  }
  .showcase-desc {
    font-size: 14px;
    color: var(--qoo-text);
    line-height: 1.8;
    margin-bottom: 16px;
  }
}
</style>
