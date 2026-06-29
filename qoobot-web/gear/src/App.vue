<template>
  <div id="qoogear-app">
    <el-container>
      <el-header class="app-header">
        <AppHeader />
      </el-header>
      <el-container>
        <el-aside v-if="showSidebar" width="220px" class="app-sidebar">
          <AppSidebar />
        </el-aside>
        <el-main class="app-main">
          <router-view />
        </el-main>
      </el-container>
      <el-footer class="app-footer">
        <AppFooter />
      </el-footer>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppFooter from '@/components/layout/AppFooter.vue'

const route = useRoute()
const showSidebar = computed(() => {
  const path = route.path
  return path.startsWith('/dev') || path.startsWith('/admin') || path.startsWith('/lab')
})
</script>

<style scoped>
.app-header { padding: 0; height: 60px; }
.app-sidebar { border-right: 1px solid #e6e6e6; min-height: calc(100vh - 100px); }
.app-main { background: #f5f7fa; min-height: calc(100vh - 100px); padding: 20px; }
.app-footer { height: 40px; text-align: center; color: #999; font-size: 12px; }
</style>
