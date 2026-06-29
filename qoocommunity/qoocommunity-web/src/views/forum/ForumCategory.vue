<template>
  <div class="forum-category">
    <div class="page-header">
      <el-breadcrumb>
        <el-breadcrumb-item :to="{ path: '/forums' }">论坛</el-breadcrumb-item>
        <el-breadcrumb-item>{{ category?.name }}</el-breadcrumb-item>
      </el-breadcrumb>
      <h1>{{ category?.name }}</h1>
      <p>{{ category?.description }}</p>
    </div>

    <div class="topic-list">
      <div v-for="topic in topics" :key="topic.id" class="page-card topic-item" @click="$router.push(`/forums/t/${topic.id}`)">
        <h3>{{ topic.title }}</h3>
        <div class="meta">
          <span>{{ topic.userId }}</span>
          <span>{{ topic.createdAt }}</span>
          <span>💬 {{ topic.replyCount }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { forumApi, type Topic, type Category } from '@/api/forum'

const route = useRoute()
const category = ref<Category | null>(null)
const topics = ref<Topic[]>([])

onMounted(async () => {
  const slug = route.params.category as string
  try {
    category.value = await forumApi.getCategory(slug)
    const result = await forumApi.getTopics({ categoryId: category.value.id })
    topics.value = result.content || []
  } catch {}
})
</script>

<style lang="scss" scoped>
.topic-item {
  cursor: pointer;
  border-bottom: 1px solid var(--qoo-border);

  h3 { font-size: 16px; margin-bottom: 6px; }
  .meta { font-size: 12px; color: var(--qoo-text-secondary); display: flex; gap: 12px; }
}
</style>
