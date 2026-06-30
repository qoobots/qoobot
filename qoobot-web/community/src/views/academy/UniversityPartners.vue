<template>
  <div class="university-page">
    <div class="page-header">
      <h1>高校合作</h1>
      <p>课程共建（机器人学/AI）、教学机器人套件、学分课程——与全球高校共建机器人教育生态</p>
    </div>

    <div class="page-card highlight-card">
      <el-row :gutter="24" align="middle">
        <el-col :span="16">
          <h2 style="font-size: 24px; color: var(--qoo-primary)">🎓 QooBot 学术合作伙伴计划</h2>
          <p style="margin: 12px 0; line-height: 1.8; color: var(--qoo-text-secondary)">
            我们与全球顶尖高校合作，提供教学机器人套件、课程资源和研究支持。无论你是教授还是学生，都能在这里找到适合你的合作方式。
          </p>
          <el-button type="primary" size="large">申请合作</el-button>
        </el-col>
        <el-col :span="8" style="text-align: center">
          <el-statistic title="合作高校" :value="48" />
          <el-statistic title="覆盖学生" :value="12500" style="margin-top: 12px" />
        </el-col>
      </el-row>
    </div>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8" v-for="prog in programs" :key="prog.title">
        <el-card class="prog-card" shadow="hover">
          <div class="prog-icon">{{ prog.icon }}</div>
          <h3>{{ prog.title }}</h3>
          <p>{{ prog.desc }}</p>
          <el-button type="primary" link>了解更多 →</el-button>
        </el-card>
      </el-col>
    </el-row>

    <div class="page-card" style="margin-top: 20px">
      <h2>🏫 合作院校</h2>
      <el-table :data="partnerSchools" stripe style="margin-top: 12px">
        <el-table-column prop="name" label="院校" width="200" />
        <el-table-column prop="program" label="合作项目" min-width="250" />
        <el-table-column prop="students" label="参与学生" width="100" />
        <el-table-column prop="since" label="合作起始" width="120" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
const programs = [
  { icon: '📚', title: '课程共建', desc: '提供机器人学、AI、计算机视觉等全套课程资源，支持学分认证。包含实验指导书、课件、评测系统。' },
  { icon: '🤖', title: '教学套件', desc: 'QooBot Edu 教学机器人套件，面向本科/研究生实验教学，含硬件+软件+课程全套方案。' },
  { icon: '🔬', title: '联合研究', desc: '与高校实验室联合开展前沿研究，提供硬件平台、算力资源和工程支持。' },
]

const partnerSchools = [
  { name: '清华大学', program: '《仿生机器人导论》课程共建 + QooBot 创新实验室', students: 320, since: '2025-09' },
  { name: '北京大学', program: 'AI 推理引擎优化联合研究', students: 85, since: '2025-06' },
  { name: '上海交通大学', program: '机器人运动规划课程 + 竞赛支持', students: 240, since: '2025-03' },
  { name: '浙江大学', program: 'SLAM 与感知联合实验室', students: 150, since: '2025-09' },
  { name: '东京大学', program: '人机交互联合研究项目', students: 60, since: '2026-01' },
]
</script>

<style lang="scss" scoped>
.highlight-card { background: linear-gradient(135deg, #f0f4ff, #e8f5e9); }
.prog-card { text-align: center; padding: 8px;
  .prog-icon { font-size: 40px; margin-bottom: 12px; }
  h3 { font-size: 17px; margin-bottom: 8px; }
  p { color: var(--qoo-text-secondary); font-size: 13px; line-height: 1.6; }
}
h2 { font-size: 20px; }
</style>
