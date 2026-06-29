<template>
  <div class="header">
    <div class="header-left">
      <el-link href="/qoogear" :underline="false" class="logo">
        <el-icon size="28"><Connection /></el-icon>
        <span class="logo-text">Made for QooBot</span>
      </el-link>
    </div>
    <div class="header-center">
      <el-menu mode="horizontal" :default-active="activeMenu" router>
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/certificates">认证配件</el-menu-item>
        <el-menu-item index="/standards">接口标准</el-menu-item>
        <el-menu-item index="/dev">开发者中心</el-menu-item>
        <el-menu-item v-if="isAdmin" index="/admin">管理后台</el-menu-item>
        <el-menu-item v-if="isLab" index="/lab">实验室</el-menu-item>
      </el-menu>
    </div>
    <div class="header-right">
      <template v-if="!isLoggedIn">
        <el-button type="primary" size="small">登录</el-button>
        <el-button size="small">注册</el-button>
      </template>
      <template v-else>
        <el-dropdown>
          <el-button type="default" size="small">
            {{ user?.name || '开发者' }} <el-icon><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>个人中心</el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const activeMenu = computed(() => {
  const p = route.path
  if (p.startsWith('/dev')) return '/dev'
  if (p.startsWith('/admin')) return '/admin'
  if (p.startsWith('/lab')) return '/lab'
  if (p.startsWith('/certificates')) return '/certificates'
  if (p.startsWith('/standards')) return '/standards'
  return '/'
})

const isLoggedIn = computed(() => auth.isLoggedIn)
const isAdmin = computed(() => auth.isAdmin)
const isLab = computed(() => auth.isLab)
const user = computed(() => auth.user)

function handleLogout() {
  auth.logout()
}
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 24px;
  border-bottom: 1px solid #e6e6e6;
  background: #fff;
}
.header-left .logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
}
.header-center { flex: 1; display: flex; justify-content: center; }
.header-center .el-menu { border-bottom: none; }
.header-right { display: flex; gap: 8px; align-items: center; }
</style>
