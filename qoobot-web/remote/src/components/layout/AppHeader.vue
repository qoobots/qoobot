<template>
  <header class="app-header">
    <div class="header-left">
      <router-link to="/" class="logo">
        <span class="logo-icon">🎮</span>
        <span class="logo-text">qooremote</span>
      </router-link>
    </div>
    <nav class="header-nav">
      <router-link to="/" class="nav-link" active-class="active">遥控面板</router-link>
      <router-link to="/sessions" class="nav-link" active-class="active">会话列表</router-link>
      <router-link to="/teaching" class="nav-link" active-class="active">示教记录</router-link>
      <router-link to="/diagnostics" class="nav-link" active-class="active">诊断</router-link>
    </nav>
    <div class="header-right">
      <div class="status-badge" :class="connectionClass">
        <span class="status-dot"></span>
        <span>{{ connectionLabel }}</span>
      </div>
      <div v-if="store.isConnected" class="latency-display">
        {{ store.latencyMs }}ms
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTeleopStore } from '@/stores/teleop'

const store = useTeleopStore()

const connectionClass = computed(() => ({
  'status-connected': store.wsConnected,
  'status-disconnected': !store.wsConnected
}))

const connectionLabel = computed(() =>
  store.wsConnected ? '已连接' : '未连接'
)
</script>

<style lang="scss" scoped>
.app-header {
  height: 56px;
  background: var(--teleop-bg-card);
  border-bottom: 1px solid var(--teleop-border);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 32px;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--teleop-text);

  .logo-icon { font-size: 24px; }
  .logo-text {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.5px;
  }
}

.header-nav {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-link {
  padding: 6px 16px;
  border-radius: 6px;
  color: var(--teleop-text-secondary);
  text-decoration: none;
  font-size: 13px;
  transition: all 0.2s;

  &:hover {
    color: var(--teleop-text);
    background: var(--teleop-bg);
  }

  &.active {
    color: var(--teleop-accent);
    background: rgba(64, 158, 255, 0.1);
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 12px;
  background: var(--teleop-bg);

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  &.status-connected {
    color: var(--teleop-success);
    .status-dot { background: var(--teleop-success); }
  }

  &.status-disconnected {
    color: var(--teleop-text-secondary);
    .status-dot { background: var(--teleop-text-secondary); }
  }
}

.latency-display {
  font-size: 13px;
  font-weight: 600;
  color: var(--teleop-accent);
  font-variant-numeric: tabular-nums;
}
</style>
