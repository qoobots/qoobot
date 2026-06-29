<template>
  <div class="event-detail" v-if="event">
    <el-breadcrumb style="margin-bottom: 16px">
      <el-breadcrumb-item :to="{ path: '/events' }">活动</el-breadcrumb-item>
      <el-breadcrumb-item>{{ event.title }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="page-card">
      <h1>{{ event.title }}</h1>
      <p class="event-meta">
        <span>📍 {{ event.location || '线上' }}</span>
        <span>🕐 {{ event.startTime }} ~ {{ event.endTime }}</span>
        <span>👥 {{ event.currentAttendees }}/{{ event.maxAttendees || '∞' }}</span>
      </p>
      <el-button type="primary" size="large" @click="register">立即报名</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { eventApi, type Event } from '@/api/event'

const route = useRoute()
const event = ref<Event | null>(null)

onMounted(async () => {
  try {
    event.value = await eventApi.getEvent(Number(route.params.id))
  } catch {}
})

async function register() {
  if (!event.value) return
  try {
    await eventApi.register(event.value.id, {})
    ElMessage.success('报名成功！')
  } catch {}
}
</script>

<style lang="scss" scoped>
.event-meta {
  display: flex;
  gap: 24px;
  margin: 16px 0 24px;
  font-size: 14px;
  color: var(--qoo-text-secondary);
}
</style>
