<template>
  <div class="video-panel">
    <div class="video-grid">
      <!-- 主摄像头 -->
      <div class="video-cell main" :class="{ active: activeStream === 'main' }"
           @click="activeStream = 'main'">
        <div class="video-placeholder">
          <el-icon :size="48"><VideoCamera /></el-icon>
          <span class="video-label">主摄像头</span>
          <span class="video-res">1080p · 30fps · H.265</span>
        </div>
        <div class="video-overlay">
          <span class="overlay-label">主视角</span>
        </div>
      </div>

      <!-- 深度相机 -->
      <div class="video-cell" :class="{ active: activeStream === 'depth' }"
           @click="activeStream = 'depth'">
        <div class="video-placeholder small">
          <el-icon :size="24"><View /></el-icon>
          <span class="video-label">深度相机</span>
        </div>
        <div class="video-overlay">
          <span class="overlay-label">深度</span>
        </div>
      </div>

      <!-- 夹爪摄像头 -->
      <div class="video-cell" :class="{ active: activeStream === 'gripper' }"
           @click="activeStream = 'gripper'">
        <div class="video-placeholder small">
          <el-icon :size="24"><Camera /></el-icon>
          <span class="video-label">夹爪摄像头</span>
        </div>
        <div class="video-overlay">
          <span class="overlay-label">夹爪</span>
        </div>
      </div>

      <!-- 后置摄像头 -->
      <div class="video-cell" :class="{ active: activeStream === 'rear' }"
           @click="activeStream = 'rear'">
        <div class="video-placeholder small">
          <el-icon :size="24"><VideoCamera /></el-icon>
          <span class="video-label">后置摄像头</span>
        </div>
        <div class="video-overlay">
          <span class="overlay-label">后方</span>
        </div>
      </div>
    </div>

    <!-- 流统计 -->
    <div v-if="streamStats.length" class="stream-stats">
      <div v-for="stat in streamStats" :key="stat.track_id" class="stat-row">
        <span class="stat-label">{{ stat.track_id }}</span>
        <span class="stat-value">{{ stat.current_bitrate_kbps }}kbps</span>
        <span class="stat-value">{{ stat.current_fps }}fps</span>
        <span class="stat-value" :class="{ 'stat-warn': stat.packet_loss_rate > 0.02 }">
          {{ (stat.packet_loss_rate * 100).toFixed(1) }}% loss
        </span>
        <span class="stat-value">{{ stat.rtt_ms }}ms</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { StreamStats } from '@/types/teleop'

defineProps<{
  streamStats?: StreamStats[]
}>()

const activeStream = ref('main')
</script>

<style lang="scss" scoped>
.video-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.video-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 6px;
  aspect-ratio: 16/9;
}

.video-cell {
  background: var(--teleop-video-bg);
  border: 2px solid var(--teleop-border);
  border-radius: 8px;
  position: relative;
  cursor: pointer;
  transition: border-color 0.2s;
  overflow: hidden;

  &.main {
    grid-row: 1 / 3;
  }

  &.active {
    border-color: var(--teleop-accent);
  }

  &:hover {
    border-color: var(--teleop-accent-hover);
  }
}

.video-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--teleop-text-secondary);

  .video-label {
    font-size: 13px;
    font-weight: 500;
  }

  .video-res {
    font-size: 11px;
    color: var(--teleop-text-secondary);
    opacity: 0.6;
  }

  &.small {
    gap: 4px;
  }
}

.video-overlay {
  position: absolute;
  top: 8px;
  left: 8px;

  .overlay-label {
    padding: 2px 8px;
    background: rgba(0, 0, 0, 0.7);
    border-radius: 4px;
    font-size: 11px;
    color: var(--teleop-text);
  }
}

.stream-stats {
  background: var(--teleop-bg-card);
  border: 1px solid var(--teleop-border);
  border-radius: 6px;
  padding: 8px 12px;
}

.stat-row {
  display: flex;
  gap: 16px;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  padding: 2px 0;

  .stat-label { color: var(--teleop-text); width: 80px; }
  .stat-value { color: var(--teleop-text-secondary); }
  .stat-warn { color: var(--teleop-warning); }
}
</style>
