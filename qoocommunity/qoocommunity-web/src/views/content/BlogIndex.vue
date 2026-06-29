<template>
  <div class="blog-index">
    <div class="page-header">
      <h1>技术博客</h1>
      <p>官方技术博客、社区投稿、工程实践分享</p>
    </div>

    <div class="blog-list">
      <div v-for="blog in blogs" :key="blog.id" class="page-card blog-card" @click="$router.push(`/blog/${blog.slug}`)">
        <div class="blog-main">
          <h3 class="blog-title">{{ blog.title }}</h3>
          <p class="blog-summary">{{ blog.summary }}</p>
          <div class="blog-meta">
            <span>{{ blog.author }}</span>
            <span>{{ blog.publishedAt || blog.createdAt }}</span>
            <span v-if="blog.tags && blog.tags.length > 0">
              <el-tag v-for="tag in blog.tags" :key="tag" size="small" style="margin-left: 4px">{{ tag }}</el-tag>
            </span>
          </div>
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

    <div v-if="blogs.length === 0" class="page-card empty-state">
      <p>暂无博客文章</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { contentApi, type Blog } from '@/api/content'

const blogs = ref<Blog[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)

onMounted(async () => {
  await loadBlogs()
})

async function loadBlogs() {
  try {
    const result = await contentApi.getBlogs({ page: currentPage.value - 1, size: pageSize.value })
    blogs.value = result.content || []
    total.value = result.total || 0
  } catch {}
}
</script>

<style lang="scss" scoped>
.blog-card {
  cursor: pointer;
  transition: all 0.2s;

  &:hover { border-color: var(--qoo-primary); }

  .blog-title { font-size: 18px; margin-bottom: 8px; }
  .blog-summary {
    font-size: 14px;
    color: var(--qoo-text-secondary);
    line-height: 1.6;
    margin-bottom: 12px;
  }
  .blog-meta {
    font-size: 12px;
    color: var(--qoo-text-secondary);
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
  }
}

.empty-state {
  text-align: center;
  color: var(--qoo-text-secondary);
  padding: 48px;
}
</style>
