import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  TeleopSession,
  TeleopState,
  TeleopCommand,
  RobotMode,
  SessionStatus,
  VideoStreamConfig,
  StreamStats
} from '@/types/teleop'
import { sessionApi } from '@/api/teleop'

export const useTeleopStore = defineStore('teleop', () => {
  // ========== 会话 ==========
  const currentSession = ref<TeleopSession | null>(null)
  const sessions = ref<TeleopSession[]>([])

  // ========== 机器人状态 ==========
  const robotState = ref<TeleopState | null>(null)
  const robotMode = ref<RobotMode>('AUTO' as RobotMode)
  const sessionStatus = ref<SessionStatus>('CLOSED' as SessionStatus)

  // ========== 视频流 ==========
  const videoStreams = ref<VideoStreamConfig[]>([])
  const streamStats = ref<StreamStats[]>([])

  // ========== 控制 ==========
  const isTeleopActive = ref(false)
  const speedOverride = ref(0.5)
  const latencyMs = ref(0)

  // ========== WebSocket ==========
  const wsConnected = ref(false)

  // ========== 计算属性 ==========
  const isConnected = computed(() => sessionStatus.value === 'ACTIVE')
  const canTakeover = computed(() => sessionStatus.value === 'ACTIVE' && robotMode.value === 'AUTO')
  const canHandover = computed(() => isTeleopActive.value)
  const batteryPercent = computed(() =>
    robotState.value ? Math.round(robotState.value.battery.state_of_charge * 100) : 0
  )
  const commQuality = computed(() => robotState.value?.system.comm_quality || 'EXCELLENT')

  // ========== 操作 ==========
  async function createSession(robotId: string, operatorId: string, mediaTypes: string[] = ['VIDEO', 'AUDIO', 'DATA']) {
    try {
      const { data } = await sessionApi.create({ robot_id: robotId, operator_id: operatorId, media_types: mediaTypes })
      if (data.code === 0) {
        currentSession.value = data.data
        sessionStatus.value = data.data.session_status
        return data.data
      }
    } catch (e) {
      console.error('Failed to create session:', e)
    }
    return null
  }

  async function requestTakeover() {
    if (!currentSession.value) return false
    try {
      await sessionApi.takeover(currentSession.value.session_id)
      robotMode.value = 'TELEOP'
      isTeleopActive.value = true
      return true
    } catch (e) {
      console.error('Takeover failed:', e)
      return false
    }
  }

  async function requestHandover() {
    if (!currentSession.value) return false
    try {
      await sessionApi.release(currentSession.value.session_id)
      robotMode.value = 'AUTO'
      isTeleopActive.value = false
      return true
    } catch (e) {
      console.error('Handover failed:', e)
      return false
    }
  }

  async function terminateSession() {
    if (!currentSession.value) return
    try {
      await sessionApi.terminate(currentSession.value.session_id)
      currentSession.value = null
      sessionStatus.value = 'CLOSED'
      isTeleopActive.value = false
      robotMode.value = 'AUTO'
    } catch (e) {
      console.error('Terminate session failed:', e)
    }
  }

  function updateRobotState(state: TeleopState) {
    robotState.value = state
    latencyMs.value = state.system.network_latency_ms
  }

  function setVideoStreams(streams: VideoStreamConfig[]) {
    videoStreams.value = streams
  }

  function updateStreamStats(stats: StreamStats[]) {
    streamStats.value = stats
  }

  function reset() {
    currentSession.value = null
    robotState.value = null
    robotMode.value = 'AUTO'
    sessionStatus.value = 'CLOSED'
    isTeleopActive.value = false
    wsConnected.value = false
  }

  return {
    // state
    currentSession,
    sessions,
    robotState,
    robotMode,
    sessionStatus,
    videoStreams,
    streamStats,
    isTeleopActive,
    speedOverride,
    latencyMs,
    wsConnected,
    // computed
    isConnected,
    canTakeover,
    canHandover,
    batteryPercent,
    commQuality,
    // actions
    createSession,
    requestTakeover,
    requestHandover,
    terminateSession,
    updateRobotState,
    setVideoStreams,
    updateStreamStats,
    reset
  }
})
