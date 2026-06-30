<template>
  <div class="good-first-issues-page">
    <div class="page-header">
      <h1>👋 新手入门任务</h1>
      <p>Good First Issues — 为初次贡献者精心挑选的入门任务，从简单开始，逐步深入</p>
    </div>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="mentor-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><UserFilled /></el-icon>
              <span>需要导师？</span>
            </div>
          </template>
          <p style="color: var(--qoo-text-secondary); line-height: 1.8">
            我们的导师计划为每位新手贡献者分配一名经验丰富的 Mentor，帮助你完成第一个 PR。
          </p>
          <el-button type="primary" style="margin-top: 12px" @click="requestMentor">申请导师</el-button>
        </el-card>
      </el-col>
      <el-col :span="16">
        <div class="page-card">
          <h2>🚀 贡献路径</h2>
          <el-steps :active="2" align-center style="margin: 20px 0">
            <el-step title="文档修正" description="修正错别字/完善文档" />
            <el-step title="简单修复" description="修复简单 Bug" />
            <el-step title="小功能" description="实现小功能模块" />
            <el-step title="独立模块" description="独立功能开发" />
            <el-step title="核心贡献" description="核心架构改进" />
          </el-steps>
        </div>
      </el-col>
    </el-row>

    <div class="page-card" style="margin-top: 20px">
      <h2>📌 当前开放的新手任务</h2>
      <el-table :data="issues" stripe style="margin-top: 16px">
        <el-table-column label="标题" min-width="300">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px">
              <el-tag :type="tagType(row.difficulty)" size="small">{{ row.difficulty }}</el-tag>
              <span style="font-weight: 500">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="120">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ row.module }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="language" label="语言" width="100" />
        <el-table-column prop="mentor" label="导师" width="120" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="claimIssue(row)">领取任务</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { UserFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const issues = [
  { title: '补充 qoobot.core.Robot 类的文档注释', module: 'qoobot-os', language: 'Python', difficulty: '初级', mentor: '@zhangwei' },
  { title: '修复 navigation 模块边界条件崩溃', module: 'qoobot-os', language: 'C++', difficulty: '中级', mentor: '@liming' },
  { title: '为控制面板添加深色模式切换', module: 'qoobot-web', language: 'TypeScript', difficulty: '初级', mentor: '@wangfang' },
  { title: '添加 LiDAR 传感器驱动的单元测试', module: 'qoobot-os', language: 'C++', difficulty: '初级', mentor: '@chenjie' },
  { title: '优化 AI 推理引擎内存池分配策略', module: 'qoobot-os', language: 'C++', difficulty: '高级', mentor: '@liuwei' },
  { title: '实现 Web 端实时日志查看器组件', module: 'qoobot-web', language: 'TypeScript/Vue', difficulty: '中级', mentor: '@zhaoling' },
]

const tagType = (d: string) => ({ '初级': 'success', '中级': 'warning', '高级': 'danger' }[d] as any)

const requestMentor = () => ElMessage.success('导师申请已提交，我们将在 24 小时内联系你')
const claimIssue = (row: any) => ElMessage.success(`已领取任务: ${row.title}`)
</script>

<style lang="scss" scoped>
.mentor-card {
  .card-header { display: flex; align-items: center; gap: 8px; font-weight: 600; }
}
h2 { font-size: 20px; }
</style>
