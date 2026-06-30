<template>
  <div class="internship-page">
    <div class="page-header">
      <h1>实习计划</h1>
      <p>QooBot 开发者实习 + 开源贡献实习（GSoC 模式）——在实践中成长，参与改变世界的机器人项目</p>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <div class="page-card">
          <h2>🚀 实习项目介绍</h2>
          <p style="line-height: 1.8; color: var(--qoo-text-secondary); margin: 12px 0">
            QooBot 实习计划面向全球在校学生，提供两种形式的实习机会：企业实习和开源贡献实习。
            无论哪种形式，你都将与顶尖工程师一起工作，参与真实的机器人项目开发。
          </p>
          <el-row :gutter="16" style="margin-top: 20px">
            <el-col :span="12">
              <el-card shadow="hover" class="type-card">
                <h3>💼 企业实习</h3>
                <ul style="line-height: 2.2; padding-left: 20px; color: var(--qoo-text-secondary); font-size: 14px">
                  <li>3-6 个月全职实习</li>
                  <li>一对一 Mentor 指导</li>
                  <li>有竞争力的实习薪资</li>
                  <li>参与核心产品开发</li>
                  <li>表现优异可获全职 Offer</li>
                </ul>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover" class="type-card">
                <h3>🌐 开源贡献实习</h3>
                <ul style="line-height: 2.2; padding-left: 20px; color: var(--qoo-text-secondary); font-size: 14px">
                  <li>3 个月远程实习 (GSoC 模式)</li>
                  <li>贡献开源项目代码</li>
                  <li>获得开源贡献奖金</li>
                  <li>社区 Mentor 指导</li>
                  <li>获得 QooBot 贡献者认证</li>
                </ul>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card">
          <h3>📅 时间线</h3>
          <el-timeline style="margin-top: 16px">
            <el-timeline-item timestamp="2026-03" type="primary">项目提案征集</el-timeline-item>
            <el-timeline-item timestamp="2026-04" type="success">申请与选拔</el-timeline-item>
            <el-timeline-item timestamp="2026-05" type="warning">入选公布</el-timeline-item>
            <el-timeline-item timestamp="2026-06~08">实习执行期</el-timeline-item>
            <el-timeline-item timestamp="2026-09" type="info">成果展示与评审</el-timeline-item>
          </el-timeline>
        </div>
        <div class="page-card" style="margin-top: 16px">
          <h3>🎯 2026 年项目方向</h3>
          <el-tag v-for="topic in topics" :key="topic" style="margin: 4px">{{ topic }}</el-tag>
        </div>
      </el-col>
    </el-row>

    <div class="page-card" style="margin-top: 20px">
      <h2>🌟 往届实习生感言</h2>
      <el-row :gutter="20">
        <el-col :span="8" v-for="alum in alumni" :key="alum.name">
          <el-card shadow="hover">
            <p style="font-style: italic; color: var(--qoo-text-secondary); line-height: 1.7">"{{ alum.quote }}"</p>
            <div style="margin-top: 12px; font-weight: 600">{{ alum.name }}</div>
            <div style="font-size: 13px; color: var(--qoo-text-secondary)">{{ alum.school }} · {{ alum.year }}</div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
const topics = ['SLAM 算法优化', '端侧 AI 推理加速', '多机器人协同', '行为树可视化', '传感器融合', 'Web 控制面板', '技能市场', '文档国际化']

const alumni = [
  { name: '张伟', school: '清华大学', year: '2025', quote: '在 QooBot 实习期间，我独自负责了导航模块的全局规划器重构，Mentor 的指导让我少走了很多弯路。' },
  { name: '李雪', school: '上海交大', year: '2025', quote: '开源贡献实习让我第一次深度参与大型开源项目，这段经历对我的技术成长帮助巨大。' },
  { name: 'Tanaka Hiro', school: '东京大学', year: '2025', quote: 'Working on the perception pipeline was challenging but incredibly rewarding. The open-source community is very welcoming.' },
]
</script>

<style lang="scss" scoped>
h2 { font-size: 20px; }
h3 { font-size: 16px; margin-bottom: 8px; }
.type-card { border-left: 3px solid var(--qoo-primary); }
</style>
