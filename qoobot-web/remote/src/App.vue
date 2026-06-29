<template>
  <el-config-provider :locale="zhCn">
    <div class="app-shell">
      <AppHeader />
      <main class="main-content">
        <router-view />
      </main>
    </div>
  </el-config-provider>
</template>

<script setup lang="ts">
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<style lang="scss" scoped>
.app-shell {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  overflow: auto;
}
</style>
