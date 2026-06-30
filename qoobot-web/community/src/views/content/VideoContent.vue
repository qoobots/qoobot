<template>
  <div class="video-content-page">
    <div class="page-header">
      <h1>视频内容</h1>
      <p>YouTube / Bilibili 教程、拆解视频、项目展示——多种方式学习 QooBot</p>
    </div>

    <el-tabs v-model="platform">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="YouTube" name="youtube" />
      <el-tab-pane label="Bilibili" name="bilibili" />
    </el-tabs>

    <el-row :gutter="20">
      <el-col v-for="video in filteredVideos" :key="video.id" :xs="24" :sm="12" :md="8" style="margin-bottom: 20px">
        <el-card class="video-card" shadow="hover">
          <div class="video-thumb" :style="{ background: video.gradient }">
            <div class="play-btn">
              <el-icon :size="48"><VideoPlay /></el-icon>
            </div>
            <span class="duration">{{ video.duration }}</span>
          </div>
          <div class="video-info">
            <h3>{{ video.title }}</h3>
            <p>{{ video.desc }}</p>
            <div class="video-meta">
              <span><el-icon><View /></el-icon> {{ formatCount(video.views) }}</span>
              <span>{{ video.date }}</span>
              <el-tag size="small">{{ video.platform }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { VideoPlay, View } from '@element-plus/icons-vue'

const platform = ref('all')

const videos = [
  { id: 1, title: 'QooBot 从零开始：硬件组装指南', desc: '完整的 QooBot 机器人硬件组装教程，从开箱到首次启动', duration: '24:30', views: 52000, date: '2026-06-20', platform: 'Bilibili', gradient: 'linear-gradient(135deg, #667eea, #764ba2)' },
  { id: 2, title: 'Building Your First Robot Skill', desc: 'Step-by-step tutorial on creating robot skills with Python SDK', duration: '18:45', views: 38000, date: '2026-06-15', platform: 'YouTube', gradient: 'linear-gradient(135deg, #f093fb, #f5576c)' },
  { id: 3, title: '深入解析阻抗控制器', desc: '原理讲解 + 参数调优 + 实战演示', duration: '32:10', views: 28000, date: '2026-06-10', platform: 'Bilibili', gradient: 'linear-gradient(135deg, #4facfe, #00f2fe)' },
  { id: 4, title: 'SLAM 导航实战：从仿真到真机', desc: '在 Gazebo 仿真和真实环境中运行 SLAM 导航', duration: '28:15', views: 35000, date: '2026-06-05', platform: 'Bilibili', gradient: 'linear-gradient(135deg, #a18cd1, #fbc2eb)' },
  { id: 5, title: 'QooBot DevCon 2026 Keynote', desc: 'Keynote presentation from QooBot Developer Conference 2026', duration: '45:00', views: 62000, date: '2026-06-01', platform: 'YouTube', gradient: 'linear-gradient(135deg, #89f7fe, #66a6ff)' },
  { id: 6, title: '多机器人协同搬运演示', desc: '两台 QooBot 协同搬运大型物体的完整演示', duration: '8:20', views: 42000, date: '2026-05-28', platform: 'YouTube', gradient: 'linear-gradient(135deg, #ffecd2, #fcb69f)' },
]

const filteredVideos = computed(() => {
  if (platform.value === 'all') return videos
  return videos.filter(v => v.platform.toLowerCase() === platform.value)
})

const formatCount = (n: number) => n >= 10000 ? (n / 10000).toFixed(1) + '万' : n.toString()
</script>

<style lang="scss" scoped>
.video-card { cursor: pointer; transition: transform .2s; &:hover { transform: translateY(-4px); } :deep(.el-card__body) { padding: 0; } }
.video-thumb {
  height: 180px; position: relative; display: flex; align-items: center; justify-content: center;
  .play-btn { color: white; opacity: .9; }
  .duration { position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,.7); color: white; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
}
.video-info { padding: 16px;
  h3 { font-size: 15px; margin-bottom: 4px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
  p { color: var(--qoo-text-secondary); font-size: 13px; margin-bottom: 8px; }
}
.video-meta { display: flex; gap: 12px; align-items: center; font-size: 12px; color: var(--qoo-text-secondary);
  span { display: flex; align-items: center; gap: 3px; }
}
</style>
