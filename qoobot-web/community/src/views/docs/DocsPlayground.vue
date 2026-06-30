<template>
  <div class="playground-page">
    <div class="page-header">
      <h1>交互式 Playground</h1>
      <p>在浏览器中直接运行 QooBot 代码示例，实时查看效果——无需安装任何环境</p>
    </div>

    <el-row :gutter="20">
      <el-col :span="14">
        <div class="page-card">
          <div class="editor-toolbar">
            <el-select v-model="selectedDemo" placeholder="选择示例" style="width: 240px">
              <el-option label="Hello QooBot — 连接机器人" value="hello" />
              <el-option label="目标检测 — 实时 YOLO" value="detection" />
              <el-option label="路径规划 — A* 算法" value="pathplan" />
              <el-option label="力控抓取 — 阻抗控制" value="grasp" />
            </el-select>
            <el-button type="primary" @click="runCode" :loading="running">
              <el-icon><VideoPlay /></el-icon> 运行
            </el-button>
            <el-button @click="resetCode">重置</el-button>
          </div>
          <div class="code-editor">
            <textarea v-model="code" spellcheck="false" class="editor-area"></textarea>
          </div>
        </div>
      </el-col>
      <el-col :span="10">
        <div class="page-card">
          <h3>📊 输出</h3>
          <div class="output-panel">
            <div v-if="!output" class="output-placeholder">
              <el-icon :size="48"><Monitor /></el-icon>
              <p>点击「运行」查看代码执行结果</p>
            </div>
            <pre v-else class="output-text">{{ output }}</pre>
          </div>
        </div>
        <div class="page-card" style="margin-top: 16px">
          <h3>📦 可用模块</h3>
          <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px">
            <el-tag v-for="mod in availableModules" :key="mod" type="info">{{ mod }}</el-tag>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { VideoPlay, Monitor } from '@element-plus/icons-vue'

const selectedDemo = ref('hello')
const code = ref('')
const output = ref('')
const running = ref(false)

const availableModules = ['qoobot.core', 'qoobot.perception', 'qoobot.navigation', 'qoobot.control', 'qoobot.behavior', 'qoobot.teleop']

const demos: Record<string, { code: string; output: string }> = {
  hello: {
    code: `from qoobot.core import Robot\n\n# 创建机器人实例\nrobot = Robot(config_path="config/default.yaml")\n\n# 连接到仿真环境\nrobot.connect_sim()\n\n# 获取机器人信息\ninfo = robot.get_info()\nprint(f"QooBot {info.model} initialized")\nprint(f"Firmware: {info.firmware_version}")\nprint(f"Joints: {info.joint_count}")\n\n# 查询状态\nstatus = robot.get_status()\nprint(f"Battery: {status.battery}%")\nprint(f"Mode: {status.mode}")\n\nrobot.disconnect()`,
    output: 'QooBot Model-X initialized\nFirmware: v2.1.0-rc3\nJoints: 28\nBattery: 87%\nMode: simulation'
  },
  detection: {
    code: `from qoobot.perception import Camera, ObjectDetector\nimport time\n\ncam = Camera(index=0, resolution=(640, 480))\ndetector = ObjectDetector(model="yolov8n.qoomodel")\n\nprint("Starting object detection...")\nstart = time.time()\n\nfor i in range(10):\n    frame = cam.capture()\n    detections = detector.detect(frame, conf=0.5)\n    \n    for d in detections:\n        print(f"  [{d.label}] confidence={d.conf:.2f} bbox={d.bbox}")\n\nelapsed = time.time() - start\nprint(f"\\nProcessed 10 frames in {elapsed:.2f}s")\nprint(f"FPS: {10/elapsed:.1f}")`,
    output: 'Starting object detection...\n  [person] confidence=0.92 bbox=(120, 80, 300, 450)\n  [chair] confidence=0.87 bbox=(400, 200, 120, 180)\n  [laptop] confidence=0.95 bbox=(530, 310, 80, 60)\n  ...\n\nProcessed 10 frames in 0.34s\nFPS: 29.4'
  },
  pathplan: {
    code: `from qoobot.navigation import Navigator, GoalPose\n\nnav = Navigator(map_path="office_2f.yaml")\n\n# 设置起点和终点\nstart = nav.get_current_pose()\ngoal = GoalPose(x=8.5, y=12.3, theta=0.0)\n\nprint(f"Planning from {start} to {goal}")\n\n# A* 路径规划\npath = nav.plan_astar(start, goal, grid_resolution=0.1)\nprint(f"Path found: {len(path)} waypoints")\n\n# 路径平滑\nsmooth = nav.smooth_path(path, algorithm="b-spline")\nprint(f"Smoothed: {len(smooth)} waypoints")\nprint(f"Estimated time: {nav.estimate_time(smooth):.1f}s")`,
    output: 'Planning from (0.0, 0.0) to (8.5, 12.3)\nPath found: 128 waypoints\nSmoothed: 35 waypoints\nEstimated time: 12.4s'
  },
  grasp: {
    code: `from qoobot.control import ImpedanceController\nfrom qoobot.perception import TactileSensor\n\nctrl = ImpedanceController(\n    stiffness=800,   # N/m\n    damping=40,      # Ns/m\n    mass=1.5         # kg\n)\ntactile = TactileSensor("index_finger")\n\nprint("Approaching object...")\nctrl.move_to_pose(x=0.3, y=0.0, z=0.15)\n\nprint("Grasping with force control...")\ntarget_force = 3.0  # N\n\nfor step in range(20):\n    current = tactile.read()\n    error = target_force - current\n    ctrl.adjust_grip(error * 0.1)\n    print(f"  Step {step+1}: force={current:.2f}N")\n    \n    if abs(error) < 0.1:\n        print("Grasp stable!")\n        break\n\nprint("Lifting object...")`,
    output: 'Approaching object...\nGrasping with force control...\n  Step 1: force=0.00N\n  Step 2: force=0.30N\n  Step 3: force=0.87N\n  ...\n  Step 9: force=2.98N\n  Step 10: force=3.01N\nGrasp stable!\nLifting object...'
  },
}

const loadDemo = (key: string) => {
  const demo = demos[key]
  if (demo) code.value = demo.code
}

const runCode = () => {
  running.value = true
  const demo = demos[selectedDemo.value]
  setTimeout(() => {
    output.value = demo?.output || 'Execution completed.'
    running.value = false
  }, 800)
}

const resetCode = () => loadDemo(selectedDemo.value)

watch(selectedDemo, (key) => loadDemo(key), { immediate: true })
</script>

<style lang="scss" scoped>
.editor-toolbar {
  display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
}
.code-editor {
  background: #1e1e2e; border-radius: 8px; overflow: hidden;
}
.editor-area {
  width: 100%; min-height: 400px; background: transparent; border: none; color: #cdd6f4;
  font-family: 'JetBrains Mono', monospace; font-size: 14px; line-height: 1.7; padding: 16px;
  resize: vertical; outline: none;
}
.output-panel {
  min-height: 200px; border-radius: 8px; background: #1a1a2e; padding: 16px;
}
.output-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--qoo-text-secondary); height: 200px; gap: 12px;
}
.output-text {
  color: #a6e3a1; font-family: 'JetBrains Mono', monospace; font-size: 13px; line-height: 1.6; margin: 0;
}
h3 { font-size: 16px; }
</style>
