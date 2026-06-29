<template>
  <el-menu :default-active="activeMenu" router class="sidebar-menu">
    <!-- 开发者中心 -->
    <template v-if="isDevSection">
      <el-menu-item index="/dev">
        <el-icon><Odometer /></el-icon>
        <span>仪表板</span>
      </el-menu-item>
      <el-menu-item index="/dev/applications">
        <el-icon><Document /></el-icon>
        <span>认证申请</span>
      </el-menu-item>
      <el-menu-item index="/dev/sdk">
        <el-icon><Download /></el-icon>
        <span>SDK 下载</span>
      </el-menu-item>
      <el-menu-item index="/dev/references">
        <el-icon><FolderOpened /></el-icon>
        <span>参考设计</span>
      </el-menu-item>
      <el-menu-item index="/dev/test-kits">
        <el-icon><SetUp /></el-icon>
        <span>测试治具</span>
      </el-menu-item>
      <el-menu-item index="/dev/docs">
        <el-icon><Reading /></el-icon>
        <span>开发文档</span>
      </el-menu-item>
      <el-menu-item index="/dev/self-check">
        <el-icon><CircleCheck /></el-icon>
        <span>认证自查</span>
      </el-menu-item>
    </template>

    <!-- 管理后台 -->
    <template v-if="isAdminSection">
      <el-menu-item index="/admin">
        <el-icon><Odometer /></el-icon>
        <span>运营仪表板</span>
      </el-menu-item>
      <el-menu-item index="/admin/applications">
        <el-icon><List /></el-icon>
        <span>申请审核</span>
      </el-menu-item>
      <el-menu-item index="/admin/certificates">
        <el-icon><Medal /></el-icon>
        <span>证书管理</span>
      </el-menu-item>
      <el-menu-item index="/admin/standards">
        <el-icon><Notebook /></el-icon>
        <span>标准管理</span>
      </el-menu-item>
      <el-menu-item index="/admin/laboratories">
        <el-icon><OfficeBuilding /></el-icon>
        <span>实验室管理</span>
      </el-menu-item>
      <el-menu-item index="/admin/security">
        <el-icon><Lock /></el-icon>
        <span>安全审计</span>
      </el-menu-item>
    </template>

    <!-- 实验室门户 -->
    <template v-if="isLabSection">
      <el-menu-item index="/lab">
        <el-icon><Odometer /></el-icon>
        <span>仪表板</span>
      </el-menu-item>
      <el-menu-item index="/lab/assignments">
        <el-icon><Tickets /></el-icon>
        <span>测试任务</span>
      </el-menu-item>
      <el-menu-item index="/lab/equipment">
        <el-icon><Cpu /></el-icon>
        <span>设备管理</span>
      </el-menu-item>
    </template>
  </el-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const isDevSection = computed(() => route.path.startsWith('/dev'))
const isAdminSection = computed(() => route.path.startsWith('/admin'))
const isLabSection = computed(() => route.path.startsWith('/lab'))
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.sidebar-menu { height: 100%; border-right: none; }
</style>
