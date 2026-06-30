<template>
  <div class="social-media-page">
    <div class="page-header">
      <h1>社交媒体</h1>
      <p>关注 QooBot 官方社交媒体账号，获取最新动态、技术分享和社区活动信息</p>
    </div>

    <el-row :gutter="20">
      <el-col :span="6" v-for="channel in channels" :key="channel.name">
        <el-card class="channel-card" shadow="hover">
          <div class="channel-icon" :style="{ background: channel.color }">{{ channel.icon }}</div>
          <h3>{{ channel.name }}</h3>
          <p style="color: var(--qoo-text-secondary); font-size: 13px; margin: 8px 0">{{ channel.desc }}</p>
          <el-statistic :value="channel.followers" :suffix="channel.suffix" style="margin: 12px 0" />
          <el-button type="primary" size="small" @click="follow(channel)">关注</el-button>
        </el-card>
      </el-col>
    </el-row>

    <div class="page-card" style="margin-top: 24px">
      <h2>📱 最新动态</h2>
      <el-timeline style="margin-top: 16px">
        <el-timeline-item v-for="post in recentPosts" :key="post.id" :timestamp="post.date" placement="top">
          <el-card>
            <p>{{ post.content }}</p>
            <div style="margin-top: 8px; display: flex; gap: 8px">
              <el-tag size="small">{{ post.platform }}</el-tag>
              <span style="font-size: 13px; color: var(--qoo-text-secondary)">
                <el-icon><Star /></el-icon> {{ post.likes }}
                <el-icon style="margin-left: 12px"><Share /></el-icon> {{ post.shares }}
              </span>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Star, Share } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const channels = [
  { name: 'Twitter / X', icon: '𝕏', color: '#1DA1F2', desc: '最新公告、技术动态', followers: 48500, suffix: ' 关注者' },
  { name: '微博', icon: '📢', color: '#E6162D', desc: '中文社区动态、活动通知', followers: 32000, suffix: ' 粉丝' },
  { name: 'Reddit', icon: '🤖', color: '#FF4500', desc: '技术讨论、社区问答', followers: 18600, suffix: ' 成员' },
  { name: 'GitHub', icon: '⭐', color: '#24292e', desc: '开源仓库、Issue 跟踪', followers: 12400, suffix: ' Stars' },
]

const recentPosts = [
  { id: 1, platform: 'Twitter', content: '🎉 QooBot v2.1.0 正式发布！新增多机器人协同 API、GPU 推理后端增强、Web 状态面板 2.0。查看更新日志 → qoobot.org/changelog', date: '2026-06-28', likes: 1280, shares: 342 },
  { id: 2, platform: '微博', content: '📢 QooBot DevCon 2026 演讲视频已全部上线 Bilibili！涵盖 SLAM、力控、AI 推理等 12 个主题。', date: '2026-06-25', likes: 960, shares: 215 },
  { id: 3, platform: 'Reddit', content: 'We just open-sourced our new AI inference engine supporting 14 chip backends. AMA in the comments!', date: '2026-06-22', likes: 2340, shares: 156 },
]

const follow = (channel: any) => ElMessage.success(`正在跳转到 ${channel.name}...`)
</script>

<style lang="scss" scoped>
.channel-card { text-align: center;
  .channel-icon { width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
    margin: 0 auto 12px; color: white; font-size: 24px; }
  h3 { font-size: 17px; }
}
h2 { font-size: 20px; }
</style>
