<script setup lang="ts">
import { onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()

onMounted(() => {
  adminStore.fetchStats()
})

const statCards = [
  { key: 'totalUsers', label: 'Total Users', icon: 'User', color: '#409eff' },
  { key: 'activeUsers', label: 'Active Users', icon: 'UserFilled', color: '#67c23a' },
  { key: 'totalDevices', label: 'Total Devices', icon: 'Monitor', color: '#e6a23c' },
  { key: 'activeSessions', label: 'Active Sessions', icon: 'Connection', color: '#909399' },
  { key: 'apiKeysActive', label: 'API Keys', icon: 'Key', color: '#f56c6c' },
  { key: 'securityAlerts', label: 'Security Alerts', icon: 'Warning', color: '#e64242' },
]
</script>

<template>
  <div class="dashboard">
    <h2 class="page-title">Dashboard</h2>

    <!-- Stats Cards -->
    <el-row :gutter="20">
      <el-col v-for="card in statCards" :key="card.key" :xs="24" :sm="12" :lg="8" class="stat-col">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">{{ card.label }}</span>
              <span class="stat-value" :style="{ color: card.color }">
                {{ (adminStore.stats as Record<string, number>)[card.key] ?? 0 }}
              </span>
            </div>
            <el-icon :size="36" :color="card.color">
              <component :is="card.icon" />
            </el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Recent Activity -->
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <span>System Overview</span>
          </template>
          <div class="overview-content">
            <el-empty description="Connect backend services to see live data" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>Quick Actions</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" plain class="action-btn">View Users</el-button>
            <el-button type="success" plain class="action-btn">Manage Devices</el-button>
            <el-button type="warning" plain class="action-btn">Audit Logs</el-button>
            <el-button type="danger" plain class="action-btn">Security Alerts</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.dashboard {
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 24px;
  }

  .stat-col {
    margin-bottom: 20px;
  }

  .stat-card {
    .stat-content {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .stat-info {
      display: flex;
      flex-direction: column;

      .stat-label {
        font-size: 13px;
        color: #909399;
        margin-bottom: 8px;
      }

      .stat-value {
        font-size: 28px;
        font-weight: 700;
      }
    }
  }

  .quick-actions {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .action-btn {
      width: 100%;
    }
  }
}
</style>
