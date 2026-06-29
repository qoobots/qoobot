<template>
  <div class="status-dashboard">
    <h3 class="dashboard-title">机器人状态</h3>

    <div class="status-grid">
      <!-- 控制模式 -->
      <div class="status-item">
        <span class="status-key">控制模式</span>
        <el-tag :type="modeTagType" size="small">{{ modeLabel }}</el-tag>
      </div>

      <!-- 会话状态 -->
      <div class="status-item">
        <span class="status-key">会话状态</span>
        <el-tag :type="sessionTagType" size="small">{{ sessionLabel }}</el-tag>
      </div>

      <!-- 延迟 -->
      <div class="status-item">
        <span class="status-key">网络延迟</span>
        <span class="status-value" :class="latencyClass">{{ latencyMs }}ms</span>
      </div>

      <!-- 通信质量 -->
      <div class="status-item">
        <span class="status-key">通信质量</span>
        <el-tag :type="commTagType" size="small">{{ commLabel }}</el-tag>
      </div>

      <!-- 电池 -->
      <div class="status-item">
        <span class="status-key">电池电量</span>
        <div class="battery-bar">
          <div class="battery-fill" :style="{ width: batteryPercent + '%' }"
               :class="batteryClass"></div>
        </div>
        <span class="status-value">{{ batteryPercent }}%</span>
      </div>

      <!-- CPU 温度 -->
      <div class="status-item">
        <span class="status-key">CPU 温度</span>
        <span class="status-value">{{ cpuTemp }}°C</span>
      </div>

      <!-- 电机温度 -->
      <div class="status-item">
        <span class="status-key">电机温度</span>
        <span class="status-value">{{ motorTemp }}°C</span>
      </div>

      <!-- 急停状态 -->
      <div class="status-item">
        <span class="status-key">急停</span>
        <el-tag :type="estopType" size="small">{{ estopLabel }}</el-tag>
      </div>

      <!-- 内存 -->
      <div class="status-item">
        <span class="status-key">内存使用</span>
        <span class="status-value">{{ memoryUsage }}%</span>
      </div>

      <!-- 运行时间 -->
      <div class="status-item">
        <span class="status-key">运行时间</span>
        <span class="status-value">{{ uptime }}</span>
      </div>
    </div>

    <!-- 安全事件 -->
    <div v-if="activeEvents.length" class="safety-events">
      <div v-for="event in activeEvents" :key="event" class="safety-event">
        <el-icon><WarningFilled /></el-icon>
        <span>{{ event }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TeleopState, RobotMode } from '@/types/teleop'

const props = defineProps<{
  state: TeleopState | null
  mode: RobotMode
  latencyMs: number
  isTeleopActive: boolean
}>()

const modeLabel = computed(() => {
  const map: Record<string, string> = { AUTO: '自主运行', HYBRID: '混合模式', TELEOP: '遥控中' }
  return map[props.mode] || props.mode
})

const modeTagType = computed(() => {
  const map: Record<string, string> = { AUTO: 'success', HYBRID: 'warning', TELEOP: '' }
  return map[props.mode] || 'info'
})

const sessionLabel = computed(() => props.isTeleopActive ? '遥控运行中' : '就绪')
const sessionTagType = computed(() => props.isTeleopActive ? '' : 'success')

const latencyClass = computed(() => ({
  'latency-ok': props.latencyMs < 100,
  'latency-warn': props.latencyMs >= 100 && props.latencyMs < 300,
  'latency-high': props.latencyMs >= 300
}))

const commLabel = computed(() => {
  const map: Record<string, string> = {
    EXCELLENT: '优秀', GOOD: '良好', FAIR: '一般', POOR: '差', LOST: '断开'
  }
  return map[props.state?.system.comm_quality || 'EXCELLENT'] || '未知'
})

const commTagType = computed(() => {
  const map: Record<string, string> = {
    EXCELLENT: 'success', GOOD: '', FAIR: 'warning', POOR: 'danger', LOST: 'danger'
  }
  return map[props.state?.system.comm_quality || 'EXCELLENT'] || 'info'
})

const batteryPercent = computed(() =>
  props.state ? Math.round(props.state.battery.state_of_charge * 100) : 0
)

const batteryClass = computed(() => ({
  'battery-low': batteryPercent.value < 20,
  'battery-warn': batteryPercent.value >= 20 && batteryPercent.value < 50
}))

const cpuTemp = computed(() => props.state?.system.cpu_temperature?.toFixed(0) || '--')
const motorTemp = computed(() => {
  if (!props.state?.joints?.length) return '--'
  const temps = props.state.joints.map(j => j.temperature).filter(t => t > 0)
  return temps.length ? Math.max(...temps).toFixed(0) : '--'
})
const memoryUsage = computed(() => props.state ? Math.round(props.state.system.memory_usage * 100) : 0)
const uptime = computed(() => {
  if (!props.state) return '--'
  const s = props.state.system.uptime_s
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}h ${m}m`
})

const estopLabel = computed(() => props.state?.safety.emergency_stop_engaged ? '已触发' : '正常')
const estopType = computed(() => props.state?.safety.emergency_stop_engaged ? 'danger' : 'success')

const activeEvents = computed(() => props.state?.safety.active_events || [])
</script>

<style lang="scss" scoped>
.status-dashboard {
  background: var(--teleop-bg-card);
  border: 1px solid var(--teleop-border);
  border-radius: 10px;
  padding: 16px;
}

.dashboard-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--teleop-text);
}

.status-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.status-key {
  color: var(--teleop-text-secondary);
  min-width: 72px;
}

.status-value {
  color: var(--teleop-text);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.latency-ok { color: var(--teleop-success) !important; }
.latency-warn { color: var(--teleop-warning) !important; }
.latency-high { color: var(--teleop-danger) !important; }

.battery-bar {
  width: 60px;
  height: 10px;
  background: var(--teleop-bg);
  border-radius: 5px;
  overflow: hidden;
}

.battery-fill {
  height: 100%;
  background: var(--teleop-success);
  border-radius: 5px;
  transition: width 0.5s;

  &.battery-warn { background: var(--teleop-warning); }
  &.battery-low { background: var(--teleop-danger); }
}

.safety-events {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.safety-event {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: rgba(245, 108, 108, 0.1);
  border-radius: 4px;
  font-size: 11px;
  color: var(--teleop-danger);
}
</style>
