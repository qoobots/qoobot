<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isLoginPage = computed(() => route.path === '/login')

const menuItems = [
  { path: '/dashboard', title: 'Dashboard', icon: 'Odometer' },
  { path: '/users', title: 'User Management', icon: 'User' },
  { path: '/devices', title: 'Device Management', icon: 'Monitor' },
  { path: '/oauth-clients', title: 'OAuth Clients', icon: 'Connection' },
  { path: '/api-keys', title: 'API Keys', icon: 'Key' },
  { path: '/audit-logs', title: 'Audit Logs', icon: 'Document' },
  { path: '/security-alerts', title: 'Security Alerts', icon: 'Warning' },
  { path: '/settings', title: 'Settings', icon: 'Setting' },
]

function handleMenuSelect(path: string) {
  router.push(path)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-container">
    <!-- Login page has its own layout -->
    <router-view v-if="isLoginPage" />

    <!-- Admin layout -->
    <el-container v-else class="admin-layout">
      <!-- Sidebar -->
      <el-aside width="240px" class="sidebar">
        <div class="sidebar-header">
          <h1 class="logo">QooAuth Admin</h1>
        </div>
        <el-menu
          :default-active="route.path"
          class="sidebar-menu"
          background-color="#001529"
          text-color="#ffffffa6"
          active-text-color="#ffffff"
          @select="handleMenuSelect"
        >
          <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- Main content -->
      <el-container>
        <el-header class="top-header">
          <div class="header-left">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/dashboard' }">Home</el-breadcrumb-item>
              <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="header-right">
            <span class="user-info">{{ authStore.user?.name || 'Admin' }}</span>
            <el-button type="danger" text @click="handleLogout">Logout</el-button>
          </div>
        </el-header>

        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<style lang="scss">
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.app-container {
  height: 100%;
}

.admin-layout {
  height: 100%;

  .sidebar {
    background-color: #001529;
    overflow-y: auto;

    .sidebar-header {
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-bottom: 1px solid #ffffff1a;

      .logo {
        color: #fff;
        font-size: 18px;
        font-weight: 600;
        white-space: nowrap;
      }
    }

    .sidebar-menu {
      border-right: none;
    }
  }

  .top-header {
    background: #fff;
    border-bottom: 1px solid #e8e8e8;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    height: 64px;

    .header-left {
      display: flex;
      align-items: center;
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 16px;

      .user-info {
        color: #666;
        font-size: 14px;
      }
    }
  }

  .main-content {
    background: #f0f2f5;
    padding: 24px;
    overflow-y: auto;
  }
}
</style>
