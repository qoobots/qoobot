<template>
  <div class="forum-index">
    <div class="page-header">
      <h1>技术论坛</h1>
      <p>讨论 QooBot 硬件、软件、技能开发与集成</p>
    </div>

    <div class="forum-layout">
      <aside class="forum-sidebar">
        <div class="sidebar-card">
          <h3>分类</h3>
          <el-menu>
            <el-menu-item v-for="cat in categories" :key="cat.slug" @click="selectCategory(cat.slug)">
              <span>{{ cat.name }}</span>
              <el-tag size="small" style="margin-left: auto">{{ cat.topicCount }}</el-tag>
            </el-menu-item>
          </el-menu>
        </div>
      </aside>

      <div class="forum-main">
        <div class="toolbar">
          <el-radio-group v-model="sortBy" size="small">
            <el-radio-button value="latest">最新</el-radio-button>
            <el-radio-button value="hot">热门</el-radio-button>
          </el-radio-group>
          <el-button type="primary" @click="showCreate = true">发布帖子</el-button>
        </div>

        <div class="topic-list">
          <div v-for="topic in topics" :key="topic.id" class="page-card topic-card" @click="$router.push(`/forums/t/${topic.id}`)">
            <div class="topic-main">
              <h3 class="topic-title">{{ topic.title }}</h3>
              <div class="topic-meta">
                <span v-if="topic.isPinned" class="pinned-tag">📌 置顶</span>
                <span>{{ topic.userId }}</span>
                <span>{{ topic.createdAt }}</span>
              </div>
            </div>
            <div class="topic-stats">
              <span>👁 {{ topic.viewCount }}</span>
              <span>💬 {{ topic.replyCount }}</span>
              <span>👍 {{ topic.likeCount }}</span>
            </div>
          </div>
        </div>

        <el-pagination
          v-if="total > pageSize"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          style="margin-top: 24px; justify-content: center"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { forumApi, type Topic, type Category } from '@/api/forum'

const categories = ref<Category[]>([])
const topics = ref<Topic[]>([])
const sortBy = ref('latest')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showCreate = ref(false)
const selectedCategory = ref('')

onMounted(async () => {
  try {
    categories.value = await forumApi.getCategories()
    const result = await forumApi.getTopics({ page: 0, size: pageSize.value })
    topics.value = result.content || []
    total.value = result.total || 0
  } catch {}
})

function selectCategory(slug: string) {
  selectedCategory.value = slug
}
</script>

<style lang="scss" scoped>
.forum-layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 24px;
}

.forum-sidebar {
  .sidebar-card {
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    box-shadow: var(--qoo-shadow);

    h3 { font-size: 16px; margin-bottom: 12px; font-weight: 600; }
  }
}

.forum-main {
  min-width: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  background: #fff;
  padding: 12px 16px;
  border-radius: 10px;
  box-shadow: var(--qoo-shadow);
}

.topic-card {
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  transition: all 0.2s;

  &:hover { border-color: var(--qoo-primary); }

  .topic-title { font-size: 16px; margin-bottom: 8px; }
  .topic-meta {
    font-size: 12px;
    color: var(--qoo-text-secondary);
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .pinned-tag { color: var(--qoo-accent); font-weight: 500; }

  .topic-stats {
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: var(--qoo-text-secondary);
    white-space: nowrap;
  }
}
</style>
