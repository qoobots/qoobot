<template>
  <div class="app-list">
    <div class="page-header">
      <h2>我的认证申请</h2>
      <el-button type="primary" @click="$router.push('/dev/applications/new')">
        <el-icon><Plus /></el-icon> 新建申请
      </el-button>
    </div>
    <el-table :data="applications" stripe>
      <el-table-column prop="applicationId" label="申请编号" width="180" />
      <el-table-column prop="productName" label="产品名称" />
      <el-table-column prop="certLevel" label="认证等级" width="120">
        <template #default="{ row }">
          <CertLevelBadge :level="row.certLevel" />
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="140">
        <template #default="{ row }">
          <CertStatusTag :status="row.status" />
        </template>
      </el-table-column>
      <el-table-column prop="submittedAt" label="提交时间" width="180" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="primary" link @click="$router.push(`/dev/applications/${row.id}`)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!applications.length" description="暂无申请" />
  </div>
</template>

<script setup lang="ts">
import CertLevelBadge from '@/components/cert/CertLevelBadge.vue'
import CertStatusTag from '@/components/cert/CertStatusTag.vue'

const applications = [
  { id: 1, applicationId: 'MFQ-2026-0003', productName: 'QooGrip Pro', certLevel: 'premium', status: 'lab_testing', submittedAt: '2026-06-15' },
  { id: 2, applicationId: 'MFQ-2026-0002', productName: 'QooSense Mini', certLevel: 'basic', status: 'certificate_issued', submittedAt: '2026-05-20' },
]
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
</style>
