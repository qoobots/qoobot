<template>
  <div class="app-detail">
    <el-page-header @back="$router.back()" title="返回列表" />
    <el-card class="detail-card">
      <template #header>
        <div class="card-header">
          <span>申请详情 — {{ app.applicationId }}</span>
          <CertStatusTag :status="app.status" />
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="申请编号">{{ app.applicationId }}</el-descriptions-item>
        <el-descriptions-item label="状态"><CertStatusTag :status="app.status" /></el-descriptions-item>
        <el-descriptions-item label="公司名称">{{ app.companyName }}</el-descriptions-item>
        <el-descriptions-item label="产品名称">{{ app.productName }}</el-descriptions-item>
        <el-descriptions-item label="认证等级"><CertLevelBadge :level="app.certLevel" /></el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ app.submittedAt }}</el-descriptions-item>
        <el-descriptions-item label="审核意见" :span="2">{{ app.reviewComment || '暂无' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="timeline-card">
      <template #header>进度时间线</template>
      <el-steps :active="activeStep" align-center>
        <el-step title="提交申请" description="2026-06-15" />
        <el-step title="审核中" description="2026-06-16" />
        <el-step title="实验室测试" description="进行中" />
        <el-step title="安全审查" />
        <el-step title="颁发证书" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import CertLevelBadge from '@/components/cert/CertLevelBadge.vue'
import CertStatusTag from '@/components/cert/CertStatusTag.vue'

const app = ref({
  applicationId: 'MFQ-2026-0003',
  companyName: 'GripTech Robotics',
  productName: 'QooGrip Pro',
  certLevel: 'premium',
  status: 'lab_testing',
  submittedAt: '2026-06-15',
  reviewComment: '产品设计符合 MFQ 规范要求，已分配实验室进行兼容性测试。',
})

const activeStep = ref(2)
</script>

<style scoped>
.detail-card { margin-top: 20px; margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.timeline-card { max-width: 900px; }
</style>
