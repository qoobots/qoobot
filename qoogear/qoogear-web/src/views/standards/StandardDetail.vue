<template>
  <div class="standard-detail-page">
    <el-page-header @back="$router.back()" title="返回标准列表" />
    <el-card class="detail-card">
      <template #header>
        <div class="card-header">
          <span>{{ spec.specNumber }} — {{ spec.title }}</span>
          <el-tag>{{ spec.version }}</el-tag>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="规范编号">{{ spec.specNumber }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ spec.version }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="spec.status === 'published' ? 'success' : 'info'">{{ spec.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="发布日期">{{ spec.publishedAt }}</el-descriptions-item>
        <el-descriptions-item label="适用配件" :span="2">
          <el-tag v-for="a in spec.appliesTo" :key="a" size="small" style="margin-right: 8px">{{ a }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ spec.description }}</el-descriptions-item>
        <el-descriptions-item label="变更日志" :span="2">{{ spec.changelog }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="versions-card">
      <template #header>版本历史</template>
      <el-timeline>
        <el-timeline-item v-for="v in versions" :key="v.version" :timestamp="v.publishedAt">
          <strong>v{{ v.version }}</strong> — {{ v.changelog }}
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const spec = ref({
  specNumber: 'MFQ-SPEC-0010',
  title: 'End Effector Standard',
  version: '1.3.0',
  status: 'published',
  publishedAt: '2026-04-01',
  appliesTo: ['gripper', 'suction_cup', 'welding_torch', '3d_print_head'],
  description: 'Defines mechanical, electrical, and communication interface requirements for QooBot end effectors.',
  changelog: 'Added support for 3D print head accessories. Updated flange specification.',
})

const versions = [
  { version: '1.3.0', publishedAt: '2026-04-01', changelog: 'Added 3D print head support' },
  { version: '1.2.0', publishedAt: '2026-02-15', changelog: 'Updated flange specification' },
  { version: '1.1.0', publishedAt: '2026-01-10', changelog: 'Added welding torch category' },
  { version: '1.0.0', publishedAt: '2025-12-01', changelog: 'Initial release' },
]
</script>

<style scoped>
.detail-card { margin-top: 20px; margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.versions-card { max-width: 600px; }
</style>
