<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

interface AuditEvent {
  eventId: string
  eventType: string
  actorId: string
  actorType: string
  targetId: string
  action: string
  outcome: string
  clientIp: string
  timestamp: string
}

const events = ref<AuditEvent[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const filterEventType = ref('')
const filterOutcome = ref('')
const dateRange = ref<[string, string] | null>(null)

const searchParams = computed(() => ({
  page: currentPage.value,
  pageSize: pageSize.value,
  eventType: filterEventType.value || undefined,
  outcome: filterOutcome.value || undefined,
}))

function handleSearch() {
  currentPage.value = 1
  ElMessage.info('Connect to audit service to search logs')
}

function getOutcomeType(outcome: string): 'success' | 'danger' | 'info' {
  switch (outcome) {
    case 'SUCCESS': return 'success'
    case 'FAILURE': return 'danger'
    case 'DENIED': return 'danger'
    default: return 'info'
  }
}
</script>

<template>
  <div class="audit-logs">
    <h2 class="page-title">Audit Logs</h2>

    <!-- Filters -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="4">
          <el-select v-model="filterEventType" placeholder="Event Type" clearable>
            <el-option label="Login" value="LOGIN" />
            <el-option label="Logout" value="LOGOUT" />
            <el-option label="Token Issue" value="TOKEN_ISSUE" />
            <el-option label="Token Revoke" value="TOKEN_REVOKE" />
            <el-option label="User Create" value="USER_CREATE" />
            <el-option label="User Delete" value="USER_DELETE" />
            <el-option label="Device Register" value="DEVICE_REGISTER" />
            <el-option label="Device Revoke" value="DEVICE_REVOKE" />
          </el-select>
        </el-col>
        <el-col :span="3">
          <el-select v-model="filterOutcome" placeholder="Outcome" clearable>
            <el-option label="Success" value="SUCCESS" />
            <el-option label="Failure" value="FAILURE" />
            <el-option label="Denied" value="DENIED" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="to"
            start-placeholder="Start date"
            end-placeholder="End date"
            value-format="YYYY-MM-DD"
          />
        </el-col>
        <el-col :span="3">
          <el-button type="primary" @click="handleSearch">Search</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- Event Table -->
    <el-card shadow="never" class="table-card">
      <el-table :data="events" v-loading="loading" stripe>
        <el-table-column prop="eventId" label="Event ID" width="120" show-overflow-tooltip />
        <el-table-column prop="eventType" label="Type" width="140" />
        <el-table-column prop="actorId" label="Actor" width="120" show-overflow-tooltip />
        <el-table-column prop="action" label="Action" min-width="150" />
        <el-table-column prop="outcome" label="Outcome" width="100">
          <template #default="{ row }">
            <el-tag :type="getOutcomeType(row.outcome)" size="small">{{ row.outcome }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="clientIp" label="IP" width="140" />
        <el-table-column prop="timestamp" label="Timestamp" width="180">
          <template #default="{ row }">
            {{ row.timestamp ? new Date(row.timestamp).toLocaleString() : '-' }}
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalCount"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.audit-logs {
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 24px;
  }

  .filter-card {
    margin-bottom: 16px;
  }

  .table-card {
    .pagination-wrapper {
      margin-top: 16px;
      display: flex;
      justify-content: flex-end;
    }
  }
}
</style>
