<template>
  <div class="lab-sponsorship-page">
    <div class="page-header">
      <h1>实验室赞助</h1>
      <p>QooBot 为高校机器人实验室提供设备赞助和联合研究支持——推动机器人技术前沿探索</p>
    </div>

    <div class="page-card banner">
      <h2>🔬 QooBot 实验室赞助计划</h2>
      <p style="margin: 12px 0; line-height: 1.8; color: var(--qoo-text-secondary); max-width: 700px">
        我们每年为 20 个高校实验室提供总额 200 万元的设备赞助。赞助内容包括 QooBot 机器人硬件平台、
        AI 推理芯片开发板、传感器模组等。同时提供技术支持和联合发表机会。
      </p>
      <div style="display: flex; gap: 12px">
        <el-button type="primary" size="large">申请赞助</el-button>
        <el-button size="large">查看指南</el-button>
      </div>
    </div>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <div class="page-card">
          <h2>📋 赞助内容</h2>
          <el-table :data="sponsorshipItems" stripe>
            <el-table-column prop="item" label="赞助项目" width="180" />
            <el-table-column prop="value" label="价值" width="120" />
            <el-table-column prop="desc" label="说明" />
          </el-table>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="page-card">
          <h2>✅ 申请条件</h2>
          <el-timeline style="margin-top: 16px">
            <el-timeline-item>高校正式注册的机器人/AI 相关实验室</el-timeline-item>
            <el-timeline-item>有明确的研究方向和发表计划</el-timeline-item>
            <el-timeline-item>愿意开源研究成果（论文/代码/数据集）</el-timeline-item>
            <el-timeline-item>承诺在赞助期内产出至少 1 篇高质量论文</el-timeline-item>
            <el-timeline-item>积极参加 QooBot 学术社区活动</el-timeline-item>
          </el-timeline>
        </div>
      </el-col>
    </el-row>

    <div class="page-card" style="margin-top: 20px">
      <h2>🏆 当前赞助实验室</h2>
      <el-row :gutter="16">
        <el-col :span="6" v-for="lab in sponsoredLabs" :key="lab.name" style="margin-bottom: 16px">
          <el-card shadow="hover">
            <h3 style="font-size: 16px">{{ lab.name }}</h3>
            <p style="font-size: 13px; color: var(--qoo-text-secondary); margin: 4px 0">{{ lab.school }}</p>
            <el-tag size="small">{{ lab.focus }}</el-tag>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
const sponsorshipItems = [
  { item: 'QooBot 机器人平台', value: '¥80,000', desc: '含完整硬件 + 1年保修' },
  { item: 'AI 推理开发套件', value: '¥30,000', desc: 'NPU/GPU 开发板 + SDK 授权' },
  { item: '传感器模组套装', value: '¥20,000', desc: '视觉/LiDAR/IMU/触觉传感器' },
  { item: '云计算资源', value: '¥50,000/年', desc: 'GPU 云端推理 + 训练资源' },
  { item: '技术支持', value: '免费', desc: '专属工程师对接 + 定期技术交流' },
]

const sponsoredLabs = [
  { name: '智能机器人实验室', school: '清华大学', focus: '全身运动控制' },
  { name: '视觉与学习实验室', school: '北京大学', focus: '3D 视觉感知' },
  { name: '自主系统实验室', school: '上海交通大学', focus: '自主导航' },
  { name: '人机交互实验室', school: '浙江大学', focus: '人机协作' },
]
</script>

<style lang="scss" scoped>
.banner { background: linear-gradient(135deg, #fef3e2, #e8f5e9); }
h2 { font-size: 20px; }
</style>
