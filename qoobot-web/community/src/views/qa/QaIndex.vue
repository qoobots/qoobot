<template>
  <div class="qa-index">
    <div class="page-header">
      <h1>问答社区</h1>
      <p>技术问答、最佳答案标记、声望系统</p>
    </div>

    <div class="toolbar">
      <el-radio-group v-model="sortBy" size="small">
        <el-radio-button value="newest">最新</el-radio-button>
        <el-radio-button value="votes">最多投票</el-radio-button>
        <el-radio-button value="unanswered">待回答</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="showCreate = true">提问</el-button>
    </div>

    <div class="question-list">
      <div v-for="q in questions" :key="q.id" class="page-card question-item" @click="$router.push(`/qa/q/${q.id}`)">
        <div class="vote-col">
          <div class="vote-count">{{ q.voteScore }}</div>
          <div class="vote-label">投票</div>
          <div class="answer-count" :class="{ solved: q.isSolved }">{{ q.answerCount }}</div>
          <div class="vote-label">回答</div>
        </div>
        <div class="question-main">
          <h3 class="question-title">{{ q.title }}</h3>
          <div class="question-meta">
            <span v-if="q.isSolved" class="solved-tag">✅ 已解决</span>
            <span>{{ q.userId }}</span>
            <span>{{ q.createdAt }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { qaApi, type Question } from '@/api/qa'

const questions = ref<Question[]>([])
const sortBy = ref('newest')
const showCreate = ref(false)

onMounted(async () => {
  try {
    const result = await qaApi.getQuestions()
    questions.value = result.content || []
  } catch {}
})
</script>

<style lang="scss" scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.question-item {
  display: flex;
  gap: 20px;
  cursor: pointer;

  .vote-col {
    text-align: center;
    min-width: 60px;

    .vote-count, .answer-count { font-size: 20px; font-weight: 700; }
    .answer-count { margin-top: 8px; }
    .answer-count.solved {
      background: var(--qoo-secondary);
      color: #fff;
      border-radius: 4px;
      padding: 2px 8px;
    }
    .vote-label { font-size: 11px; color: var(--qoo-text-secondary); }
  }

  .question-main {
    .question-title { font-size: 16px; margin-bottom: 8px; }
    .question-meta {
      font-size: 12px;
      color: var(--qoo-text-secondary);
      display: flex;
      gap: 12px;
    }
    .solved-tag { color: var(--qoo-secondary); font-weight: 500; }
  }
}
</style>
