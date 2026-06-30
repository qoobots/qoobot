<template>
  <div class="transparency-page">
    <div class="page-header">
      <h1>透明度报告</h1>
      <p>年度社区报告、贡献统计、财务透明——QooBot 对社区负责</p>
    </div>

    <el-tabs v-model="activeYear">
      <el-tab-pane v-for="report in reports" :key="report.year" :label="`${report.year} 年度报告`" :name="report.year.toString()">
        <div class="page-card">
          <h2>📊 {{ report.year }} 年度概览</h2>
          <el-row :gutter="20" style="margin-top: 20px">
            <el-col :span="6" v-for="stat in report.stats" :key="stat.label">
              <el-statistic :title="stat.label" :value="stat.value" :suffix="stat.suffix" />
            </el-col>
          </el-row>
        </div>

        <el-row :gutter="20" style="margin-top: 20px">
          <el-col :span="12">
            <div class="page-card">
              <h3>👥 社区增长</h3>
              <el-table :data="report.growth" stripe>
                <el-table-column prop="metric" label="指标" width="200" />
                <el-table-column prop="q1" label="Q1" width="80" />
                <el-table-column prop="q2" label="Q2" width="80" />
                <el-table-column prop="q3" label="Q3" width="80" />
                <el-table-column prop="q4" label="Q4" width="80" />
              </el-table>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="page-card">
              <h3>💰 财务透明</h3>
              <el-table :data="report.finances" stripe>
                <el-table-column prop="category" label="类别" width="160" />
                <el-table-column prop="amount" label="金额 (万元)" width="120" />
                <el-table-column prop="note" label="备注" />
              </el-table>
            </div>
          </el-col>
        </el-row>

        <div class="page-card" style="margin-top: 20px">
          <h3>🏆 里程碑</h3>
          <el-timeline>
            <el-timeline-item v-for="m in report.milestones" :key="m.date" :timestamp="m.date">
              {{ m.event }}
            </el-timeline-item>
          </el-timeline>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeYear = ref('2025')

const reports = [
  {
    year: 2025,
    stats: [
      { label: '注册开发者', value: 18500, suffix: '' },
      { label: '代码提交', value: 52000, suffix: '' },
      { label: '活跃贡献者', value: 386, suffix: '' },
      { label: '社区活动', value: 48, suffix: ' 场' },
    ],
    growth: [
      { metric: '新注册用户', q1: '3200', q2: '4100', q3: '5200', q4: '6000' },
      { metric: '活跃仓库', q1: '12', q2: '15', q3: '18', q4: '22' },
      { metric: '论坛帖子', q1: '2800', q2: '3500', q3: '4200', q4: '5100' },
      { metric: 'Q&A 解答数', q1: '1200', q2: '1500', q3: '1900', q4: '2400' },
    ],
    finances: [
      { category: '基础设施', amount: '120', note: '云服务/CI/CD/域名' },
      { category: '活动组织', amount: '80', note: 'DevCon/黑客松/Meetup' },
      { category: '社区运营', amount: '60', note: '内容创作/翻译/社区管理' },
      { category: '开发者激励', amount: '100', note: '贡献奖金/奖学金/赞助' },
      { category: '总支出', amount: '360', note: '全部来自企业赞助和捐赠' },
    ],
    milestones: [
      { date: '2025-01', event: 'QooBot 核心仓库在 GitHub 开源' },
      { date: '2025-03', event: '社区注册开发者突破 5000 人' },
      { date: '2025-06', event: '首届 QooBot DevCon 在北京举办' },
      { date: '2025-09', event: '技能市场上线，首批 50 个技能发布' },
      { date: '2025-12', event: '年度贡献者颁奖典礼' },
    ],
  },
]
</script>

<style lang="scss" scoped>
h2 { font-size: 20px; }
h3 { font-size: 16px; margin-bottom: 10px; }
</style>
