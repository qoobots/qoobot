<template>
  <div class="teleop-panel">
    <!-- 视频 + 状态行 -->
    <div class="top-row">
      <div class="video-area">
        <VideoPanel :stream-stats="store.streamStats" />
      </div>
      <div class="status-area">
        <StatusDashboard
          :state="store.robotState"
          :mode="store.robotMode"
          :latency-ms="store.latencyMs"
          :is-teleop-active="store.isTeleopActive"
        />
      </div>
    </div>

    <!-- 控制 + 紧急操作 -->
    <div class="bottom-row">
      <div class="control-area">
        <ControlPanel
          :enabled="store.isTeleopActive"
          @move="onMove"
          @joint="onJoint"
          @gripper="onGripper"
          @head="onHead"
          @speed-change="onSpeedChange"
        />
      </div>
      <div class="actions-area">
        <EmergencyBar
          :is-teleop-active="store.isTeleopActive"
          :is-connected="store.isConnected"
          :is-estop-engaged="store.robotState?.safety.emergency_stop_engaged ?? false"
          @emergency-stop="onEmergencyStop"
          @takeover="onTakeover"
          @handover="onHandover"
          @toggle-recording="onToggleRecording"
          @toggle-voice="onToggleVoice"
        />

        <!-- 会话信息 -->
        <div v-if="store.currentSession" class="session-info">
          <div class="info-row">
            <span class="info-key">会话 ID</span>
            <span class="info-value mono">{{ store.currentSession.session_id.slice(0, 12) }}...</span>
          </div>
          <div class="info-row">
            <span class="info-key">机器人</span>
            <span class="info-value">{{ store.currentSession.robot_id }}</span>
          </div>
          <div class="info-row">
            <span class="info-key">操作员</span>
            <span class="info-value">{{ store.currentSession.operator_id }}</span>
          </div>
          <div class="info-row">
            <span class="info-key">指令计数</span>
            <span class="info-value">{{ store.currentSession.command_count }}</span>
          </div>
        </div>

        <!-- 关节状态 -->
        <div v-if="store.robotState?.joints?.length" class="joint-states">
          <h4 class="section-title">关节状态</h4>
          <div v-for="j in store.robotState.joints.slice(0, 6)" :key="j.joint_name" class="joint-state-row">
            <span class="joint-name">{{ j.joint_name }}</span>
            <span class="joint-pos">{{ j.position.toFixed(3) }}</span>
            <span class="joint-temp" :class="{ 'temp-warn': j.temperature > 60 }">
              {{ j.temperature.toFixed(0) }}°C
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useTeleopStore } from '@/stores/teleop'
import VideoPanel from '@/components/teleop/VideoPanel.vue'
import StatusDashboard from '@/components/teleop/StatusDashboard.vue'
import ControlPanel from '@/components/teleop/ControlPanel.vue'
import EmergencyBar from '@/components/teleop/EmergencyBar.vue'

const store = useTeleopStore()

// ========== WebSocket 信令 ==========
let ws: WebSocket | null = null

function connectWebSocket(sessionId: string) {
  const baseUrl = import.meta.env.VITE_WS_BASE_URL || `ws://${location.host}/ws/teleop`
  ws = new WebSocket(`${baseUrl}/${sessionId}`)

  ws.onopen = () => {
    store.wsConnected = true
    console.log('[TeleopPanel] WebSocket connected')
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      switch (msg.type) {
        case 'robot.status':
          store.updateRobotState(msg.payload)
          break
        case 'session.update':
          if (store.currentSession) {
            store.currentSession = { ...store.currentSession, ...msg.payload }
          }
          break
        case 'robot.sensor':
          // 传感器数据更新
          break
      }
    } catch (e) {
      console.warn('[TeleopPanel] Invalid WS message:', e)
    }
  }

  ws.onclose = () => {
    store.wsConnected = false
    console.log('[TeleopPanel] WebSocket disconnected')
    // 自动重连
    setTimeout(() => {
      if (store.isConnected) {
        connectWebSocket(sessionId)
      }
    }, 3000)
  }

  ws.onerror = (err) => {
    console.error('[TeleopPanel] WebSocket error:', err)
  }
}

function sendCommand(cmd: any) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(cmd))
  }
}

// ========== 控制事件处理 ==========
function onMove(vx: number, vy: number, omega: number) {
  sendCommand({
    type: 'control',
    command: { fullbody: { base: { vx, vy, omega }, speed_override: store.speedOverride } }
  })
}

function onJoint(name: string, position: number) {
  sendCommand({
    type: 'control',
    command: { joint: { joint_name: name, position } }
  })
}

function onGripper(side: 'left' | 'right', action: 'open' | 'close') {
  const position = action === 'open' ? 0.08 : 0.0
  sendCommand({
    type: 'control',
    command: { gripper: { side, position } }
  })
}

function onHead(pitch: number, yaw: number) {
  sendCommand({
    type: 'control',
    command: { head: { pitch, yaw, roll: 0 } }
  })
}

function onSpeedChange(value: number) {
  store.speedOverride = value
}

async function onTakeover() {
  const success = await store.requestTakeover()
  if (success && store.currentSession) {
    connectWebSocket(store.currentSession.session_id)
  }
}

async function onHandover() {
  await store.requestHandover()
  if (ws) {
    ws.close()
    ws = null
  }
}

function onEmergencyStop() {
  sendCommand({
    type: 'teleop.emergency_stop',
    payload: { reason: 'Operator triggered emergency stop' }
  })
  store.terminateSession()
  if (ws) {
    ws.close()
    ws = null
  }
}

function onToggleRecording() {
  sendCommand({
    type: 'teaching',
    action: 'toggle'
  })
}

function onToggleVoice() {
  sendCommand({
    type: 'media',
    action: 'toggle_voice'
  })
}

// ========== 生命周期 ==========
onMounted(() => {
  // 如果已有会话，建立 WebSocket 连接
  if (store.currentSession?.session_id) {
    connectWebSocket(store.currentSession.session_id)
  }
})

onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }
})
</script>

<style lang="scss" scoped>
.teleop-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  max-width: 1600px;
  margin: 0 auto;
}

.top-row {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 12px;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
}

.video-area {
  min-height: 360px;
}

.status-area {
  min-width: 300px;
}

.bottom-row {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 12px;

  @media (max-width: 1024px) {
    grid-template-columns: 1fr;
  }
}

.control-area {
  min-width: 0;
}

.actions-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.session-info {
  background: var(--teleop-bg-card);
  border: 1px solid var(--teleop-border);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.info-key {
  color: var(--teleop-text-secondary);
}

.info-value {
  color: var(--teleop-text);

  &.mono {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 11px;
  }
}

.joint-states {
  background: var(--teleop-bg-card);
  border: 1px solid var(--teleop-border);
  border-radius: 10px;
  padding: 14px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--teleop-text-secondary);
  margin-bottom: 8px;
}

.joint-state-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-size: 11px;

  .joint-name {
    color: var(--teleop-text-secondary);
    flex: 1;
  }

  .joint-pos {
    color: var(--teleop-text);
    font-variant-numeric: tabular-nums;
    min-width: 54px;
    text-align: right;
  }

  .joint-temp {
    color: var(--teleop-text-secondary);
    min-width: 36px;
    text-align: right;

    &.temp-warn { color: var(--teleop-warning); }
  }
}
</style>
