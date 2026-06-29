<template>
  <div class="event-index">
    <div class="page-header">
      <h1>活动中心</h1>
      <p>开发者大会、黑客松、技术分享、线上活动</p>
    </div>

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="DevCon" name="DEVCON" />
      <el-tab-pane label="黑客松" name="HACKATHON" />
      <el-tab-pane label="技术分享" name="TECHTALK" />
      <el-tab-pane label="线上活动" name="WEBINAR" />
      <el-tab-pane label="Meetup" name="MEETUP" />
    </el-tabs>

    <div v-if="!loading && events.length === 0" class="page-card empty-state">
      <el-empty :description="`暂无${tabLabel(activeTab)}活动`" />
    </div>

    <div v-else class="event-grid">
      <div v-for="event in events" :key="event.id" class="page-card event-card" @click="$router.push(`/events/${event.id}`)">
        <div class="event-cover" :style="{ background: gradientFor(event.type) }">
          <span class="event-type-badge">{{ typeLabel(event.type) }}</span>
        </div>
        <div class="event-info">
          <h3>{{ event.title }}</h3>
          <p class="event-location">{{ event.location || '🌐 线上' }}</p>
          <p class="event-time">{{ formatTime(event.startTime) }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { eventApi, type Event } from '@/api/event'

const events = ref<Event[]>([])
const activeTab = ref('all')
const loading = ref(true)

const typeLabel = (t: string) => {
  const map: Record<string, string> = {
    DEVCON: 'DevCon', HACKATHON: '黑客松', TECHTALK: '技术分享',
    WEBINAR: '线上活动', MEETUP: 'Meetup'
  }
  return map[t] || t
}

const tabLabel = (t: string) => {
  const map: Record<string, string> = {
    all: '全部', DEVCON: 'DevCon', HACKATHON: '黑客松',
    TECHTALK: '技术分享', WEBINAR: '线上活动', MEETUP: 'Meetup'
  }
  return map[t] || t
}

const fetchEvents = async (type?: string) => {
  loading.value = true
  try {
    events.value = await eventApi.getEvents({ type } as any)
  } catch { } finally {
    loading.value = false
  }
}

const handleTabChange = (tab: string) => {
  if (tab === 'all') {
    fetchEvents()
  } else {
    fetchEvents(tab)
  }
}

const formatTime = (t: string) => {
  try {
    return new Date(t).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return t
  }
}

onMounted(() => fetchEvents())

function gradientFor(type: string): string {
  const gradients: Record<string, string> = {
    'DEVCON': 'linear-gradient(135deg, #667eea, #764ba2)',
    'HACKATHON': 'linear-gradient(135deg, #f093fb, #f5576c)',
    'TECHTALK': 'linear-gradient(135deg, #4facfe, #00f2fe)',
    'WEBINAR': 'linear-gradient(135deg, #43e97b, #38f9d7)',
    'MEETUP': 'linear-gradient(135deg, #fa709a, #fee140)'
  }
  return gradients[type] || 'linear-gradient(135deg, #4A90D9, #34C759)'
}
</script>

<style lang="scss" scoped>
.event-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.event-card {
  cursor: pointer;
  overflow: hidden;
  padding: 0;
  transition: transform 0.2s;

  &:hover { transform: translateY(-2px); }

  .event-cover {
    height: 120px;
    display: flex;
    align-items: flex-start;
    justify-content: flex-end;
    padding: 12px;
  }

  .event-type-badge {
    background: rgba(255,255,255,0.25);
    color: #fff;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }

  .event-info {
    padding: 16px;

    h3 { font-size: 16px; margin-bottom: 8px; }
    p { font-size: 13px; color: var(--qoo-text-secondary); margin-bottom: 4px; }
    .event-location { font-weight: 500; }
  }
}
</style>
