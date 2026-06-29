<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { userApi, type User, type UserListParams } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'

const users = ref<User[]>([])
const totalCount = ref(0)
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const filterState = ref('')

const searchParams = computed<UserListParams>(() => ({
  page: currentPage.value,
  pageSize: pageSize.value,
  search: searchQuery.value || undefined,
  state: filterState.value || undefined,
}))

async function fetchUsers() {
  loading.value = true
  try {
    const data = await userApi.list(searchParams.value)
    users.value = data.users
    totalCount.value = data.totalCount
  } catch {
    ElMessage.error('Failed to load users')
  } finally {
    loading.value = false
  }
}

async function handleFreeze(user: User) {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to freeze user "${user.email}"?`,
      'Confirm Freeze',
      { type: 'warning' }
    )
    if (user.state === 'FROZEN') {
      await userApi.unfreeze(user.userId)
      ElMessage.success(`User ${user.email} unfrozen`)
    } else {
      await userApi.freeze(user.userId)
      ElMessage.success(`User ${user.email} frozen`)
    }
    await fetchUsers()
  } catch {
    // Cancelled
  }
}

async function handleDelete(user: User) {
  try {
    await ElMessageBox.confirm(
      `Are you sure you want to delete user "${user.email}"? This action cannot be undone.`,
      'Confirm Delete',
      { type: 'error', confirmButtonText: 'Delete', confirmButtonClass: 'el-button--danger' }
    )
    await userApi.delete(user.userId)
    ElMessage.success(`User ${user.email} deleted`)
    await fetchUsers()
  } catch {
    // Cancelled
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchUsers()
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchUsers()
}

function getStateType(state: string): 'success' | 'danger' | 'warning' | 'info' {
  switch (state) {
    case 'ACTIVE': return 'success'
    case 'FROZEN': return 'warning'
    case 'DELETED': return 'danger'
    default: return 'info'
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="user-management">
    <h2 class="page-title">User Management</h2>

    <!-- Search & Filters -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <el-input
            v-model="searchQuery"
            placeholder="Search by email or name..."
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filterState" placeholder="State" clearable @change="handleSearch">
            <el-option label="Active" value="ACTIVE" />
            <el-option label="Frozen" value="FROZEN" />
            <el-option label="Deleted" value="DELETED" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="handleSearch">Search</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- User Table -->
    <el-card shadow="never" class="table-card">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="userId" label="User ID" width="120" show-overflow-tooltip />
        <el-table-column prop="email" label="Email" min-width="200" />
        <el-table-column prop="displayName" label="Name" min-width="150" />
        <el-table-column prop="roles" label="Roles" width="150">
          <template #default="{ row }">
            <el-tag v-for="role in row.roles" :key="role" size="small" style="margin-right: 4px">
              {{ role.replace('ROLE_', '') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="state" label="State" width="100">
          <template #default="{ row }">
            <el-tag :type="getStateType(row.state)" size="small">{{ row.state }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLoginAt" label="Last Login" width="180">
          <template #default="{ row }">
            {{ row.lastLoginAt ? new Date(row.lastLoginAt).toLocaleString() : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              size="small"
              :type="row.state === 'FROZEN' ? 'success' : 'warning'"
              @click="handleFreeze(row)"
            >
              {{ row.state === 'FROZEN' ? 'Unfreeze' : 'Freeze' }}
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              Delete
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
          @size-change="fetchUsers"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.user-management {
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
