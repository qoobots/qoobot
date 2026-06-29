<template>
  <div class="dev-dashboard">
    <h2>开发者仪表板</h2>
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">3</div>
          <div class="stat-label">认证申请</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">2</div>
          <div class="stat-label">已获认证</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">1</div>
          <div class="stat-label">审核中</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">5</div>
          <div class="stat-label">SDK 下载</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="quick-actions">
      <template #header>快捷操作</template>
      <el-row :gutter="16">
        <el-col :span="6" v-for="a in actions" :key="a.label">
          <el-button :type="a.type" style="width: 100%; height: 80px" @click="$router.push(a.route)">
            <el-icon :size="20"><component :is="a.icon" /></el-icon>
            <div style="margin-top: 8px">{{ a.label }}</div>
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="recent-apps">
      <template #header>最近申请</template>
      <el-table :data="recentApps" stripe>
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
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import CertLevelBadge from '@/components/cert/CertLevelBadge.vue'
import CertStatusTag from '@/components/cert/CertStatusTag.vue'

const actions = [
  { label: '新建申请', icon: 'Plus', route: '/dev/applications/new', type: 'primary' },
  { label: '下载 SDK', icon: 'Download', route: '/dev/sdk', type: 'success' },
  { label: '参考设计', icon: 'FolderOpened', route: '/dev/references', type: 'warning' },
  { label: '认证自查', icon: 'CircleCheck', route: '/dev/self-check', type: '' },
]

const recentApps = [
  { applicationId: 'MFQ-2026-0003', productName: 'QooGrip Pro', certLevel: 'premium', status: 'lab_testing', submittedAt: '2026-06-15' },
  { applicationId: 'MFQ-2026-0002', productName: 'QooSense Mini', certLevel: 'basic', status: 'certificate_issued', submittedAt: '2026-05-20' },
  { applicationId: 'MFQ-2026-0001', productName: 'QooCharge Lite', certLevel: 'basic', status: 'certificate_issued', submittedAt: '2026-04-10' },
]
</script>

<style scoped>
.stats-row { margin-bottom: 20px; }
.stat-card { text-align: center; }
.stat-value { font-size: 32px; font-weight: 700; color: #409eff; }
.stat-label { color: #909399; margin-top: 8px; }
.quick-actions { margin-bottom: 20px; }
.recent-apps { }
</style>
