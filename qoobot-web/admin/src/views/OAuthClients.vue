<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

interface OAuthClient {
  clientId: string
  clientName: string
  grantTypes: string[]
  redirectUris: string[]
  scopes: string[]
  state: string
  createdAt: string
}

const clients = ref<OAuthClient[]>([])
const loading = ref(false)

// Placeholder - connect to actual API endpoint when available
const columns = [
  { prop: 'clientId', label: 'Client ID', width: 200 },
  { prop: 'clientName', label: 'Name', minWidth: 150 },
  { prop: 'grantTypes', label: 'Grant Types', width: 200 },
  { prop: 'scopes', label: 'Scopes', width: 200 },
  { prop: 'state', label: 'State', width: 100 },
]

function handleAdd() {
  ElMessage.info('Client registration form coming soon')
}

function handleEdit(client: OAuthClient) {
  ElMessage.info(`Edit client: ${client.clientId}`)
}

function handleDelete(client: OAuthClient) {
  ElMessage.info(`Delete client: ${client.clientId}`)
}
</script>

<template>
  <div class="oauth-clients">
    <div class="page-header">
      <h2 class="page-title">OAuth Clients</h2>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        Register Client
      </el-button>
    </div>

    <el-card shadow="never" class="table-card">
      <el-table :data="clients" v-loading="loading" stripe>
        <el-table-column
          v-for="col in columns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth"
        >
          <template v-if="col.prop === 'state'" #default="{ row }">
            <el-tag :type="row.state === 'ACTIVE' ? 'success' : 'danger'" size="small">
              {{ row.state }}
            </el-tag>
          </template>
          <template v-else-if="col.prop === 'grantTypes' || col.prop === 'scopes'" #default="{ row }">
            <el-tag v-for="item in row[col.prop]" :key="item" size="small" style="margin: 2px">
              {{ item }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">Edit</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && clients.length === 0" description="No OAuth clients registered" />
    </el-card>
  </div>
</template>

<style scoped>
.oauth-clients {
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
  }

  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #1a1a1a;
    margin: 0;
  }
}
</style>
