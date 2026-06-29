<template>
  <div class="emergency-bar">
    <el-button
      type="danger"
      size="large"
      :icon="WarningFilled"
      class="estop-btn"
      @click="onEmergencyStop"
    >
      紧急停止
    </el-button>

    <el-button
      v-if="isTeleopActive"
      type="warning"
      size="large"
      @click="onHandover"
    >
      交还自主
    </el-button>

    <el-button
      v-if="!isTeleopActive && isConnected"
      type="primary"
      size="large"
      @click="onTakeover"
    >
      接管控制
    </el-button>

    <el-button
      :type="isRecording ? 'danger' : 'default'"
      size="large"
      :icon="VideoCamera"
      @click="onToggleRecording"
    >
      {{ isRecording ? '停止录制' : '示教录制' }}
    </el-button>

    <el-button
      size="large"
      :icon="Microphone"
      @click="onToggleVoice"
    >
      语音对讲
    </el-button>

    <div class="estop-status">
      <el-tag v-if="isEstopEngaged" type="danger" size="large">
        急停已触发
      </el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { WarningFilled, VideoCamera, Microphone } from '@element-plus/icons-vue'
import { ref } from 'vue'

defineProps<{
  isTeleopActive: boolean
  isConnected: boolean
  isEstopEngaged: boolean
}>()

const emit = defineEmits<{
  (e: 'emergency-stop'): void
  (e: 'takeover'): void
  (e: 'handover'): void
  (e: 'toggle-recording'): void
  (e: 'toggle-voice'): void
}>()

const isRecording = ref(false)

function onEmergencyStop() {
  emit('emergency-stop')
}

function onTakeover() {
  emit('takeover')
}

function onHandover() {
  emit('handover')
}

function onToggleRecording() {
  isRecording.value = !isRecording.value
  emit('toggle-recording')
}

function onToggleVoice() {
  emit('toggle-voice')
}
</script>

<style lang="scss" scoped>
.emergency-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--teleop-bg-card);
  border: 1px solid var(--teleop-border);
  border-radius: 10px;
  flex-wrap: wrap;
}

.estop-btn {
  font-weight: 700;
  letter-spacing: 2px;
  min-width: 120px;
}

.estop-status {
  margin-left: auto;
}
</style>
