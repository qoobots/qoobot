<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { deviceApi, type Device, type DeviceListParams } from '@/api/devices'
import { ElMessage, ElMessageBox } from 'element-plus'

const devices = ref<Device[]>([])
const totalCount = ref(0)
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const filterState = ref('')
const filterType = ref('')

const searchParams = computed<DeviceListParams>(() => ({
  page: currentPage.value,
  pageSize: pageSize.value,
  state: filterState.value || undefined,
  deviceType: filterType.value || undefined,
}))

async function fetchDevices() {
  loading.value = true
  try {
    const data = await deviceApi.list(searchParams.value)
    devices.value = data.devices
    totalCount.value = data.totalCount
  } catch {
    ElMessage.error('Failed to load devices')
  } finally {
    loading.value = false
  }
}

async function handleLock(device: Device) {
  try {
    if (device.state === 'LOCKED') {
      await deviceApi.unlock(device.deviceId)
      ElMessage.success(`Device ${device.deviceName} unlocked`)
    } else {
      await deviceApi.lock(device.deviceId)
      ElMessage.success(`Device ${device.deviceName} locked`)
    }
    await fetchDevices()
  } catch {
    ElMessage.error('Operation failed')
  }
}

async function handleWipe(device: Device) {
  try {
    await ElMessageBox.confirm(
      `This will remotely wipe device "${device.deviceName}". This action cannot be undone.`,
      'Confirm Remote Wipe',
      { type: 'error', confirmButtonText: 'Wipe Device' }
    )
    await deviceApi.wipe(device.deviceId)
    ElMessage.success(`Wipe command sent to ${device.deviceName}`)
    await fetchDevices()
  } catch {
    // Cancelled
  }
}

async function handleRevoke(device: Device) {
  try {
    await ElMessageBox.confirm(
      `Revoke access for device "${device.deviceName}"?`,
      'Confirm Revoke',
      { type: 'warning' }
    )
    await deviceApi.revoke(device.deviceId)
    ElMessage.success(`Device ${device.deviceName} revoked`)
    await fetchDevices()
  } catch {
    // Cancelled
  }
}

function getStateType(state: string): 'success' | 'danger' | 'warning' | 'info' {
  switch (state) {
    case 'ACTIVE': return 'success'
    case 'LOCKED': return 'warning'
    case 'WIPED': return 'danger'
    case 'REVOKED': return 'info'
    default: return 'info'
  }
}

onMounted(fetchDevices)
</script>

<template>
  <div class="device-management">
    <h2 class="page-title">Device Management</h2>

    <el-card shadow="never" class="filter-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="4">
          <el-select v-model="filterState" placeholder="State" clearable @change="fetchDevices">
            <el-option label="Active" value="ACTIVE" />
            <el-option label="Locked" value="LOCKED" />
            <el-option label="Wiped" value="WIPED" />
            <el-option label="Revoked" value="REVOKED" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterType" placeholder="Type" clearable @change="fetchDevices">
            <el-option label="Robot" value="robot" />
            <el-option label="Desktop" value="desktop" />
            <el-option label="Mobile" value="mobile" />
            <el-option label="Embedded" value="embedded" />
          </el-select>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="devices" v-loading="loading" stripe>
        <el-table-column prop="deviceId" label="Device ID" width="120" show-overflow-tooltip />
        <el-table-column prop="deviceName" label="Name" min-width="150" />
        <el-table-column prop="deviceType" label="Type" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.deviceType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="serialNumber" label="Serial Number" width="160" />
        <el-table-column prop="state" label="State" width="100">
          <template #default="{ row }">
            <el-tag :type="getStateType(row.state)" size="small">{{ row.state }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastSeenAt" label="Last Seen" width="180">
          <template #default="{ row }">
            {{ row.lastSeenAt ? new Date(row.lastSeenAt).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="240" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              :type="row.state === 'LOCKED' ? 'success' : 'warning'"
              @click="handleLock(row)"
              :disabled="row.state === 'WIPED' || row.state === 'REVOKED'"
            >
              {{ row.state === 'LOCKED' ? 'Unlock' : 'Lock' }}
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleWipe(row)"
              :disabled="row.state === 'WIPED' || row.state === 'REVOKED'"
            >
              Wipe
            </el-button>
            <el-button
              size="small"
              type="info"
              @click="handleRevoke(row)"
              :disabled="row.state === 'REVOKED'"
            >
              Revoke
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalCount"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchDevices"
          @current-change="(p: number) => { currentPage = p; fetchDevices() }"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.device-management {
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
