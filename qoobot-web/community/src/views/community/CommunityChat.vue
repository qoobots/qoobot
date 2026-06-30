<template>
  <div class="community-chat-page">
    <div class="page-header">
      <h1>即时通讯社区</h1>
      <p>加入 QooBot 官方 Discord / Slack 社区——实时交流、技术支持、社群互动</p>
    </div>

    <el-row :gutter="24">
      <el-col :span="12">
        <el-card class="platform-card discord-card" shadow="hover">
          <div class="platform-header">
            <div class="platform-icon discord-icon">🎮</div>
            <div>
              <h2>Discord 社区</h2>
              <p style="color: var(--qoo-text-secondary)">实时聊天 + 语音频道 + 机器人自动问答</p>
            </div>
          </div>
          <el-divider />
          <div class="channel-list">
            <h3>频道分类</h3>
            <el-tag v-for="ch in discordChannels" :key="ch" class="channel-tag" type="info">{{ ch }}</el-tag>
          </div>
          <div style="margin-top: 20px; text-align: center">
            <el-statistic title="在线成员" :value="2847" style="margin-bottom: 16px" />
            <el-button type="primary" size="large" @click="joinDiscord">
              <el-icon><ChatDotRound /></el-icon> 加入 Discord
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="platform-card slack-card" shadow="hover">
          <div class="platform-header">
            <div class="platform-icon slack-icon">💬</div>
            <div>
              <h2>Slack 工作区</h2>
              <p style="color: var(--qoo-text-secondary)">专业讨论 + 频道分类 + 文件共享</p>
            </div>
          </div>
          <el-divider />
          <div class="channel-list">
            <h3>频道分类</h3>
            <el-tag v-for="ch in slackChannels" :key="ch" class="channel-tag" type="info">{{ ch }}</el-tag>
          </div>
          <div style="margin-top: 20px; text-align: center">
            <el-statistic title="注册成员" :value="4520" style="margin-bottom: 16px" />
            <el-button type="success" size="large" @click="joinSlack">
              <el-icon><ChatLineSquare /></el-icon> 加入 Slack
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="page-card" style="margin-top: 24px">
      <h2>🤖 社区机器人</h2>
      <p style="color: var(--qoo-text-secondary); margin-bottom: 16px">我们的社区机器人会自动回答常见问题、搜索文档、引导新成员</p>
      <el-collapse>
        <el-collapse-item title="@QooHelper — 智能问答助手" name="1">
          <p>自动搜索文档和论坛回答技术问题。支持自然语言查询，如：</p>
          <el-tag style="margin: 4px">"如何使用行为树引擎？"</el-tag>
          <el-tag style="margin: 4px" type="success">"qoobot.navigation 怎么配置？"</el-tag>
          <el-tag style="margin: 4px" type="warning">"我的机器人连不上了怎么办？"</el-tag>
        </el-collapse-item>
        <el-collapse-item title="@QooRelease — 版本发布通知" name="2">
          <p>自动推送 SDK/固件/文档更新通知到社区频道</p>
        </el-collapse-item>
        <el-collapse-item title="@QooMod — 社区管理" name="3">
          <p>自动欢迎新成员、执行社区规范、报告违规内容</p>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChatDotRound, ChatLineSquare } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const discordChannels = ['#general', '#dev-chat', '#hardware', '#perception', '#navigation', '#showcase', '#jobs', '#off-topic']
const slackChannels = ['#announcements', '#core-dev', '#app-dev', '#cloud', '#qa-help', '#random']

const joinDiscord = () => ElMessage.success('正在跳转到 Discord 邀请链接...')
const joinSlack = () => ElMessage.success('正在跳转到 Slack 邀请链接...')
</script>

<style lang="scss" scoped>
.platform-card {
  min-height: 360px;
  h2 { font-size: 22px; }
}
.platform-header { display: flex; align-items: center; gap: 16px; }
.platform-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 28px; }
.discord-icon { background: #5865F2; } .slack-icon { background: #4A154B; }
.channel-list {
  h3 { font-size: 15px; margin-bottom: 8px; }
}
.channel-tag { margin: 4px; }
h2 { font-size: 20px; }
</style>
