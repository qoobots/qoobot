<template>
  <div class="control-panel">
    <!-- 移动控制 -->
    <div class="control-section">
      <h4 class="section-title">移动控制</h4>
      <div class="dpad">
        <button class="dpad-btn up" @mousedown="startMove(0, 1)" @mouseup="stopMove"
                @touchstart.prevent="startMove(0, 1)" @touchend.prevent="stopMove">
          <el-icon><CaretTop /></el-icon>
        </button>
        <button class="dpad-btn left" @mousedown="startMove(-1, 0)" @mouseup="stopMove"
                @touchstart.prevent="startMove(-1, 0)" @touchend.prevent="stopMove">
          <el-icon><CaretLeft /></el-icon>
        </button>
        <button class="dpad-btn center" disabled></button>
        <button class="dpad-btn right" @mousedown="startMove(1, 0)" @mouseup="stopMove"
                @touchstart.prevent="startMove(1, 0)" @touchend.prevent="stopMove">
          <el-icon><CaretRight /></el-icon>
        </button>
        <button class="dpad-btn down" @mousedown="startMove(0, -1)" @mouseup="stopMove"
                @touchstart.prevent="startMove(0, -1)" @touchend.prevent="stopMove">
          <el-icon><CaretBottom /></el-icon>
        </button>
      </div>
      <div class="speed-control">
        <span class="speed-label">速度倍率</span>
        <el-slider v-model="speed" :min="10" :max="100" :step="5"
                   :disabled="!enabled" @input="onSpeedChange" />
        <span class="speed-value">{{ speed }}%</span>
      </div>
    </div>

    <!-- 手臂控制 -->
    <div class="control-section">
      <h4 class="section-title">手臂控制</h4>
      <div class="joint-sliders">
        <div v-for="joint in joints" :key="joint.name" class="joint-row">
          <span class="joint-name">{{ joint.label }}</span>
          <el-slider v-model="joint.value" :min="joint.min" :max="joint.max"
                     :step="0.01" :disabled="!enabled" @input="onJointChange(joint.name, $event)" />
          <span class="joint-value">{{ joint.value.toFixed(2) }}</span>
        </div>
      </div>
      <div class="gripper-controls">
        <el-button-group>
          <el-button :disabled="!enabled" @click="onGripper('left', 'close')">
            <el-icon><Lock /></el-icon> 左夹爪闭合
          </el-button>
          <el-button :disabled="!enabled" @click="onGripper('left', 'open')">
            左夹爪张开
          </el-button>
        </el-button-group>
        <el-button-group>
          <el-button :disabled="!enabled" @click="onGripper('right', 'close')">
            <el-icon><Lock /></el-icon> 右夹爪闭合
          </el-button>
          <el-button :disabled="!enabled" @click="onGripper('right', 'open')">
            右夹爪张开
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 头部控制 -->
    <div class="control-section">
      <h4 class="section-title">头部控制</h4>
      <div class="head-controls">
        <div class="head-row">
          <span>俯仰</span>
          <el-slider v-model="headPitch" :min="-90" :max="90" :step="1"
                     :disabled="!enabled" @input="onHeadChange" />
          <span>{{ headPitch }}°</span>
        </div>
        <div class="head-row">
          <span>偏航</span>
          <el-slider v-model="headYaw" :min="-180" :max="180" :step="1"
                     :disabled="!enabled" @input="onHeadChange" />
          <span>{{ headYaw }}°</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

const props = defineProps<{
  enabled: boolean
}>()

const emit = defineEmits<{
  (e: 'move', vx: number, vy: number, omega: number): void
  (e: 'joint', name: string, position: number): void
  (e: 'gripper', side: 'left' | 'right', action: 'open' | 'close'): void
  (e: 'head', pitch: number, yaw: number): void
  (e: 'speed-change', value: number): void
}>()

// 速度
const speed = ref(50)
function onSpeedChange(val: number) {
  emit('speed-change', val / 100)
}

// 移动控制
const moveInterval = ref<ReturnType<typeof setInterval> | null>(null)

function startMove(vx: number, vy: number) {
  stopMove()
  emit('move', vx * speed.value / 100, vy * speed.value / 100, 0)
  moveInterval.value = setInterval(() => {
    emit('move', vx * speed.value / 100, vy * speed.value / 100, 0)
  }, 50)
}

function stopMove() {
  if (moveInterval.value) {
    clearInterval(moveInterval.value)
    moveInterval.value = null
  }
  emit('move', 0, 0, 0)
}

// 关节
const joints = reactive([
  { name: 'arm_shoulder_pitch', label: '肩部俯仰', value: 0, min: -1.57, max: 1.57 },
  { name: 'arm_shoulder_roll', label: '肩部滚转', value: 0, min: -1.57, max: 1.57 },
  { name: 'arm_elbow', label: '肘部', value: -1.2, min: -2.0, max: 0.0 },
  { name: 'arm_wrist_pitch', label: '腕部俯仰', value: 0, min: -1.57, max: 1.57 }
])

function onJointChange(name: string, value: number) {
  emit('joint', name, value)
}

// 夹爪
function onGripper(side: 'left' | 'right', action: 'open' | 'close') {
  emit('gripper', side, action)
}

// 头部
const headPitch = ref(0)
const headYaw = ref(0)
function onHeadChange() {
  emit('head', (headPitch.value * Math.PI) / 180, (headYaw.value * Math.PI) / 180)
}
</script>

<style lang="scss" scoped>
.control-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.control-section {
  background: var(--teleop-bg-card);
  border: 1px solid var(--teleop-border);
  border-radius: 10px;
  padding: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--teleop-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

// D-Pad
.dpad {
  display: grid;
  grid-template-columns: 56px 56px 56px;
  grid-template-rows: 56px 56px 56px;
  gap: 4px;
  justify-content: center;
  margin-bottom: 12px;

  .up { grid-column: 2; grid-row: 1; }
  .left { grid-column: 1; grid-row: 2; }
  .center { grid-column: 2; grid-row: 2; }
  .right { grid-column: 3; grid-row: 2; }
  .down { grid-column: 2; grid-row: 3; }
}

.dpad-btn {
  width: 56px;
  height: 56px;
  border: 1px solid var(--teleop-border);
  border-radius: 8px;
  background: var(--teleop-dpad-bg);
  color: var(--teleop-text);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  font-size: 20px;

  &:hover:not(:disabled) {
    background: var(--teleop-dpad-active);
    border-color: var(--teleop-accent);
  }

  &:active:not(:disabled) {
    background: var(--teleop-accent);
    color: white;
    transform: scale(0.95);
  }

  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
}

// Speed
.speed-control {
  display: flex;
  align-items: center;
  gap: 10px;
}

.speed-label {
  font-size: 11px;
  color: var(--teleop-text-secondary);
  white-space: nowrap;
}

.speed-value {
  font-size: 12px;
  color: var(--teleop-accent);
  font-weight: 600;
  min-width: 36px;
  text-align: right;
}

// Joints
.joint-sliders {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.joint-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.joint-name {
  font-size: 11px;
  color: var(--teleop-text-secondary);
  min-width: 72px;
}

.joint-value {
  font-size: 11px;
  color: var(--teleop-text);
  min-width: 44px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

// Grippers
.gripper-controls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

// Head
.head-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.head-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;

  span:first-child {
    color: var(--teleop-text-secondary);
    min-width: 40px;
  }

  span:last-child {
    color: var(--teleop-text);
    min-width: 40px;
    text-align: right;
  }
}
</style>
