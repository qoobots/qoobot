<template>
  <div class="blog-detail" v-if="blog">
    <el-breadcrumb style="margin-bottom: 16px">
      <el-breadcrumb-item :to="{ path: '/blog' }">博客</el-breadcrumb-item>
      <el-breadcrumb-item>{{ blog.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-card blog-header">
      <h1>{{ blog.title }}</h1>
      <div class="blog-meta">
        <span>{{ blog.author }}</span>
        <span>{{ blog.publishedAt || blog.createdAt }}</span>
        <span v-if="blog.tags && blog.tags.length > 0">
          <el-tag v-for="tag in blog.tags" :key="tag" size="small" style="margin-left: 4px">{{ tag }}</el-tag>
        </span>
      </div>
    </div>

    <div class="page-card blog-content">
      <MarkdownViewer :content="blog.content" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { contentApi, type Blog } from '@/api/content'
import MarkdownViewer from '@/components/common/MarkdownViewer.vue'

const route = useRoute()
const blog = ref<Blog | null>(null)

onMounted(async () => {
  try {
    blog.value = await contentApi.getBlog(route.params.slug as string)
  } catch {}
})
</script>

<style lang="scss" scoped>
.blog-header {
  h1 { font-size: 24px; margin-bottom: 12px; }
  .blog-meta {
    font-size: 13px;
    color: var(--qoo-text-secondary);
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
  }
}

.blog-content {
  min-height: 200px;
}
</style>
