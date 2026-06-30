<template>
  <div class="docs-versioning-page">
    <div class="page-header">
      <h1>版本化文档</h1>
      <p>按 QooBot 版本切换文档，查看废弃 API 标注和迁移指南</p>
    </div>

    <div class="page-card">
      <el-tabs v-model="activeVersion" type="border-card" @tab-click="onVersionChange">
        <el-tab-pane v-for="v in versions" :key="v.key" :label="v.label" :name="v.key">
          <el-alert v-if="v.key !== 'latest'" :title="`你正在查看 ${v.label} 版本文档`" type="warning" :closable="false" show-icon style="margin-bottom: 16px">
            <template #default>
              <span>此版本已进入维护模式。建议升级到 <el-button type="primary" link @click="activeVersion = 'latest'">最新版本</el-button></span>
            </template>
          </el-alert>

          <h3>{{ v.label }} 新增功能</h3>
          <el-timeline style="margin-top: 16px">
            <el-timeline-item v-for="item in v.features" :key="item.title" :timestamp="item.date" placement="top">
              <el-card>
                <h4>{{ item.title }}</h4>
                <p style="color: var(--qoo-text-secondary); margin-top: 4px">{{ item.desc }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div class="page-card" style="margin-top: 20px">
      <h2>⚠️ 废弃 API</h2>
      <el-table :data="deprecatedApis" stripe>
        <el-table-column prop="api" label="API" width="280" />
        <el-table-column prop="deprecatedIn" label="废弃版本" width="120" />
        <el-table-column prop="removalIn" label="计划移除" width="120" />
        <el-table-column prop="migration" label="迁移方案" min-width="250" />
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeVersion = ref('latest')

const versions = [
  {
    key: 'latest', label: 'v2.1 (Latest)',
    features: [
      { title: '多机器人协同 API', desc: '新增 CollaborationManager 用于多机器人任务协调', date: '2026-06' },
      { title: 'GPU 推理后端增强', desc: '支持 CUDA 12 + OpenCL 3.0 统一抽象', date: '2026-05' },
      { title: 'Web 状态面板 2.0', desc: '全新的行为树可视化编辑器', date: '2026-04' },
    ]
  },
  {
    key: 'v2.0', label: 'v2.0 (LTS)',
    features: [
      { title: '感知模块重构', desc: '统一的传感器融合管道，支持热插拔', date: '2025-12' },
      { title: 'AI 推理引擎', desc: '端侧推理 NPU 支持，ONNX 模型导入', date: '2025-11' },
    ]
  },
  {
    key: 'v1.0', label: 'v1.0 (EOL)',
    features: [
      { title: '初始版本', desc: '核心控制与感知功能', date: '2025-06' },
    ]
  },
]

const deprecatedApis = [
  { api: 'qoobot.perception.LegacyCamera', deprecatedIn: 'v2.0', removalIn: 'v2.2', migration: '使用 qoobot.perception.Camera' },
  { api: 'qoobot.control.PIDController (旧接口)', deprecatedIn: 'v2.0', removalIn: 'v2.2', migration: '使用 qoobot.control.ImpedanceController' },
  { api: 'qoobot.navigation.GridPlanner', deprecatedIn: 'v1.0', removalIn: '已移除', migration: '使用 qoobot.navigation.HybridPlanner' },
]

const onVersionChange = () => {}
</script>

<style lang="scss" scoped>
h2 { font-size: 20px; }
h3 { font-size: 17px; margin-bottom: 8px; }
h4 { font-size: 15px; }
</style>
