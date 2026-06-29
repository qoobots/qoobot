<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

interface ApiKeyInfo {
  keyId: string
  name: string
  userId: string
  state: string
  createdAt: string
  expiresAt: string | null
  lastUsedAt: string | null
}

const apiKeys = ref<ApiKeyInfo[]>([])
const loading = ref(false)

function getStateType(state: string): 'success' | 'danger' | 'warning' | 'info' {
  switch (state) {
    case 'ACTIVE': return 'success'
    case 'REVOKED': return 'danger'
    case 'EXPIRED': return 'warning'
    default: return 'info'
  }
}

async function handleRevoke(key: ApiKeyInfo) {
  try {
    await ElMessageBox.confirm(
      `Revoke API key "${key.name}"? This action cannot be undone.`,
      'Confirm Revoke',
      { type: 'warning' }
    )
    ElMessage.success(`API key "${key.name}" revoked`)
  } catch {
    // Cancelled
  }
}
</script>

<template>
  <div class="api-keys">
    <h2 class="page-title">API Keys</h2>

    <el-card shadow="never" class="table-card">
      <el-table :data="apiKeys" v-loading="loading" stripe>
        <el-table-column prop="keyId" label="Key ID" width="140" show-overflow-tooltip />
        <el-table-column prop="name" label="Name" min-width="150" />
        <el-table-column prop="userId" label="User ID" width="140" show-overflow-tooltip />
        <el-table-column prop="state" label="State" width="100">
          <template #default="{ row }">
            <el-tag :type="getStateType(row.state)" size="small">{{ row.state }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="Created" width="180">
          <template #default="{ row }">
            {{ row.createdAt ? new Date(row.createdAt).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="expiresAt" label="Expires" width="180">
          <template #default="{ row }">
            {{ row.expiresAt ? new Date(row.expiresAt).toLocaleString() : 'Never' }}
          </template>
        </el-table-column>
        <el-table-column prop="lastUsedAt" label="Last Used" width="180">
          <template #default="{ row }">
            {{ row.lastUsedAt ? new Date(row.lastUsedAt).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              type="danger"
              :disabled="row.state !== 'ACTIVE'"
              @click="handleRevoke(row)"
            >
              Revoke
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && apiKeys.length === 0" description="No API keys found" />
    </el-card>
  </div>
</template>

<style scoped>
.api-keys {
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 24px;
  }
}
</style>
