<template>
  <div class="question-view" v-if="question">
    <el-breadcrumb style="margin-bottom: 16px">
      <el-breadcrumb-item :to="{ path: '/qa' }">问答</el-breadcrumb-item>
      <el-breadcrumb-item>{{ question.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-card">
      <h1>{{ question.title }}</h1>
      <div class="q-info">
        <span>{{ question.userId }}</span>
        <span>{{ question.createdAt }}</span>
        <span>👁 {{ question.viewCount }}</span>
      </div>
      <MarkdownViewer :content="question.content" class="q-content" />
      <div class="vote-buttons">
        <el-button @click="vote('up')">👍 {{ question.voteScore }}</el-button>
        <el-button @click="vote('down')">👎</el-button>
      </div>
    </div>

    <div class="answers-section">
      <h3>回答 ({{ answers.length }})</h3>
      <div v-for="a in answers" :key="a.id" class="page-card answer-item">
        <MarkdownViewer :content="a.content" />
        <div class="answer-footer">
          <span>{{ a.userId }}</span>
          <span>{{ a.createdAt }}</span>
        </div>
      </div>
    </div>

    <div class="page-card">
      <h3>你的回答</h3>
      <el-input v-model="answerContent" type="textarea" :rows="4" placeholder="输入答案（支持 Markdown）..." />
      <el-button type="primary" style="margin-top: 12px" @click="submitAnswer">提交回答</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { qaApi, type Question } from '@/api/qa'
import MarkdownViewer from '@/components/common/MarkdownViewer.vue'

const route = useRoute()
const question = ref<Question | null>(null)
const answers = ref<any[]>([])
const answerContent = ref('')

onMounted(async () => {
  const id = Number(route.params.id)
  try {
    question.value = await qaApi.getQuestion(id)
    answers.value = await qaApi.getAnswers(id)
  } catch {}
})

function vote(type: string) {
  if (!question.value) return
  qaApi.vote('question', question.value.id, type)
}

async function submitAnswer() {
  if (!question.value || !answerContent.value.trim()) return
  try {
    await qaApi.createAnswer(question.value.id, { content: answerContent.value, contentHtml: answerContent.value })
    answerContent.value = ''
    const id = Number(route.params.id)
    answers.value = await qaApi.getAnswers(id)
  } catch {}
}
</script>

<style lang="scss" scoped>
.q-info {
  font-size: 13px;
  color: var(--qoo-text-secondary);
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.q-content { margin: 16px 0; }

.vote-buttons {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.answers-section { margin-top: 24px; }

.answer-item {
  .answer-footer {
    font-size: 12px;
    color: var(--qoo-text-secondary);
    display: flex;
    gap: 12px;
    margin-top: 12px;
  }
}
</style>
