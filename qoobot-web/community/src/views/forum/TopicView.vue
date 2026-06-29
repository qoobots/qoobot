<template>
  <div class="topic-view" v-if="topic">
    <el-breadcrumb style="margin-bottom: 16px">
      <el-breadcrumb-item :to="{ path: '/forums' }">论坛</el-breadcrumb-item>
      <el-breadcrumb-item>{{ topic.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-card topic-header">
      <h1>{{ topic.title }}</h1>
      <div class="topic-info">
        <span>{{ topic.userId }}</span>
        <span>{{ topic.createdAt }}</span>
        <span>👁 {{ topic.viewCount }}</span>
        <span>💬 {{ topic.replyCount }}</span>
      </div>
    </div>

    <div class="page-card topic-content">
      <MarkdownViewer :content="topic.content" />
    </div>

    <div class="topic-actions">
      <el-button @click="toggleLike">
        <el-icon><Star /></el-icon>
        {{ topic.likeCount }} 赞
      </el-button>
      <el-button @click="toggleBookmark">
        <el-icon><Collection /></el-icon>
        收藏
      </el-button>
    </div>

    <div class="replies-section">
      <h3>回复 ({{ replies.length }})</h3>
      <div v-for="reply in replies" :key="reply.id" class="page-card reply-item">
        <div class="reply-header">
          <span class="reply-author">{{ reply.userId }}</span>
          <span class="reply-time">{{ reply.createdAt }}</span>
        </div>
        <MarkdownViewer :content="reply.content" />
      </div>
    </div>

    <div class="page-card reply-editor">
      <h3>发表回复</h3>
      <el-input
        v-model="replyContent"
        type="textarea"
        :rows="4"
        placeholder="输入回复内容（支持 Markdown）..."
      />
      <el-button type="primary" style="margin-top: 12px" @click="submitReply">提交回复</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Star, Collection } from '@element-plus/icons-vue'
import { forumApi, type Topic } from '@/api/forum'
import MarkdownViewer from '@/components/common/MarkdownViewer.vue'

const route = useRoute()
const topic = ref<Topic | null>(null)
const replies = ref<any[]>([])
const replyContent = ref('')

onMounted(async () => {
  const id = Number(route.params.id)
  try {
    topic.value = await forumApi.getTopic(id)
    replies.value = await forumApi.getReplies(id)
  } catch {}
})

function toggleLike() {
  if (!topic.value) return
  forumApi.toggleLike('topic', topic.value.id)
}

function toggleBookmark() {
  if (!topic.value) return
  forumApi.toggleBookmark(topic.value.id)
}

async function submitReply() {
  if (!topic.value || !replyContent.value.trim()) return
  try {
    await forumApi.createReply(topic.value.id, { content: replyContent.value, contentHtml: replyContent.value })
    replyContent.value = ''
    replies.value = await forumApi.getReplies(topic.value.id)
  } catch {}
}
</script>

<style lang="scss" scoped>
.topic-header {
  h1 { font-size: 24px; margin-bottom: 12px; }
  .topic-info {
    font-size: 13px;
    color: var(--qoo-text-secondary);
    display: flex;
    gap: 16px;
  }
}

.topic-content {
  min-height: 100px;
}

.topic-actions {
  display: flex;
  gap: 12px;
  margin: 16px 0;
}

.replies-section {
  margin-top: 24px;

  h3 { font-size: 18px; margin-bottom: 16px; }
}

.reply-item {
  .reply-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
    font-size: 13px;

    .reply-author { font-weight: 600; }
    .reply-time { color: var(--qoo-text-secondary); }
  }
}

.reply-editor {
  margin-top: 24px;

  h3 { font-size: 16px; margin-bottom: 12px; }
}
</style>
