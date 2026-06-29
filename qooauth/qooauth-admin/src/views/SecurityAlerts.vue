<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface SecurityAlert {
  alertId: string
  severity: string
  category: string
  title: string
  description: string
  source: string
  status: string
  detectedAt: string
  resolvedAt: string | null
}

const alerts = ref<SecurityAlert[]>([])
const loading = ref(false)
const filterSeverity = ref('')
const filterStatus = ref('')

function getSeverityType(severity: string): 'danger' | 'warning' | 'info' | '' {
  switch (severity) {
    case 'CRITICAL': return 'danger'
    case 'HIGH': return 'danger'
    case 'MEDIUM': return 'warning'
    case 'LOW': return 'info'
    default: return ''
  }
}

function getStatusType(status: string): 'warning' | 'success' | 'info' {
  switch (status) {
    case 'OPEN': return 'warning'
    case 'RESOLVED': return 'success'
    case 'DISMISSED': return 'info'
    default: return 'info'
  }
}

function handleResolve(alert: SecurityAlert) {
  ElMessage.success(`Alert ${alert.alertId} resolved`)
}

function handleDismiss(alert: SecurityAlert) {
  ElMessage.info(`Alert ${alert.alertId} dismissed`)
}
</script>

<template>
  <div class="security-alerts">
    <h2 class="page-title">Security Alerts</h2>

    <!-- Filters -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="4">
          <el-select v-model="filterSeverity" placeholder="Severity" clearable>
            <el-option label="Critical" value="CRITICAL" />
            <el-option label="High" value="HIGH" />
            <el-option label="Medium" value="MEDIUM" />
            <el-option label="Low" value="LOW" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterStatus" placeholder="Status" clearable>
            <el-option label="Open" value="OPEN" />
            <el-option label="Resolved" value="RESOLVED" />
            <el-option label="Dismissed" value="DISMISSED" />
          </el-select>
        </el-col>
      </el-row>
    </el-card>

    <!-- Alerts List -->
    <el-card shadow="never" class="table-card">
      <el-table :data="alerts" v-loading="loading" stripe>
        <el-table-column prop="severity" label="Severity" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="Category" width="140" />
        <el-table-column prop="title" label="Title" min-width="200" show-overflow-tooltip />
        <el-table-column prop="description" label="Description" min-width="250" show-overflow-tooltip />
        <el-table-column prop="source" label="Source" width="120" />
        <el-table-column prop="status" label="Status" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="detectedAt" label="Detected" width="180">
          <template #default="{ row }">
            {{ row.detectedAt ? new Date(row.detectedAt).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'OPEN'"
              size="small"
              type="success"
              @click="handleResolve(row)"
            >
              Resolve
            </el-button>
            <el-button
              v-if="row.status === 'OPEN'"
              size="small"
              type="info"
              @click="handleDismiss(row)"
            >
              Dismiss
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && alerts.length === 0" description="No security alerts" />
    </el-card>
  </div>
</template>

<style scoped>
.security-alerts {
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 24px;
  }

  .filter-card {
    margin-bottom: 16px;
  }
}
</style>
