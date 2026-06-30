<template>
  <div class="docs-api-page">
    <div class="page-header">
      <h1>API 文档</h1>
      <p>完整的 Python / C++ SDK API 参考，自动生成，交互式示例</p>
    </div>

    <el-row :gutter="24">
      <el-col :span="6">
        <div class="page-card api-sidebar">
          <el-menu :default-active="activeApi" @select="handleApiSelect">
            <el-sub-menu index="python">
              <template #title><el-icon><Coin /></el-icon> Python SDK</template>
              <el-menu-item index="python-core">qoobot.core — 核心模块</el-menu-item>
              <el-menu-item index="python-perception">qoobot.perception — 感知模块</el-menu-item>
              <el-menu-item index="python-motion">qoobot.motion — 运动规划</el-menu-item>
              <el-menu-item index="python-control">qoobot.control — 实时控制</el-menu-item>
              <el-menu-item index="python-behavior">qoobot.behavior — 行为树</el-menu-item>
              <el-menu-item index="python-teleop">qoobot.teleop — 远程遥控</el-menu-item>
            </el-sub-menu>
            <el-sub-menu index="cpp">
              <template #title><el-icon><Cpu /></el-icon> C++ SDK</template>
              <el-menu-item index="cpp-hal">qoobot::hal — 硬件抽象层</el-menu-item>
              <el-menu-item index="cpp-ai">qoobot::ai — AI 推理引擎</el-menu-item>
              <el-menu-item index="cpp-comm">qoobot::comm — 通信总线</el-menu-item>
              <el-menu-item index="cpp-safety">qoobot::safety — 安全监护</el-menu-item>
            </el-sub-menu>
            <el-sub-menu index="rest">
              <template #title><el-icon><Connection /></el-icon> REST API</template>
              <el-menu-item index="rest-auth">认证接口 /api/v1/auth</el-menu-item>
              <el-menu-item index="rest-device">设备管理 /api/v1/devices</el-menu-item>
              <el-menu-item index="rest-cloud">云端推理 /api/v1/inference</el-menu-item>
              <el-menu-item index="rest-ota">OTA 升级 /api/v1/ota</el-menu-item>
            </el-sub-menu>
          </el-menu>
        </div>
      </el-col>
      <el-col :span="18">
        <div class="page-card api-content" v-if="activeApi === 'python-core'">
          <h2>qoobot.core — 核心模块 <el-tag size="small" type="success">Python</el-tag></h2>
          <p class="api-desc">提供 QooBot 机器人的核心控制接口，包括初始化、生命周期管理、基础状态查询等。</p>

          <h3>初始化</h3>
          <div class="api-example">
            <pre><code class="language-python">from qoobot.core import Robot

# 创建机器人实例
robot = Robot(config_path="config/robot.yaml")

# 连接到机器人
robot.connect(host="192.168.1.100", port=9090)

# 获取机器人状态
status = robot.get_status()
print(f"Battery: {status.battery}%")
print(f"Temperature: {status.temperature}°C")
print(f"Mode: {status.mode}")</code></pre>
          </div>

          <h3>Robot 类参考</h3>
          <el-table :data="coreApiTable" border stripe style="margin-top: 12px">
            <el-table-column prop="method" label="方法" width="240" />
            <el-table-column prop="desc" label="描述" />
            <el-table-column prop="returns" label="返回值" width="200" />
          </el-table>

          <h3>Status 数据类</h3>
          <el-table :data="statusFields" border stripe style="margin-top: 12px">
            <el-table-column prop="field" label="字段" width="180" />
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="desc" label="描述" />
          </el-table>
        </div>

        <div class="page-card api-content" v-else-if="activeApi === 'python-perception'">
          <h2>qoobot.perception — 感知模块 <el-tag size="small" type="success">Python</el-tag></h2>
          <p class="api-desc">多模态感知接口，提供视觉、听觉、触觉、力觉传感器数据的获取与处理。</p>
          <h3>快速开始</h3>
          <div class="api-example">
            <pre><code class="language-python">from qoobot.perception import Camera, Lidar, Microphone

cam = Camera(index=0, resolution=(1920, 1080))
frame = await cam.capture()
objects = await cam.detect_objects(frame)

lidar = Lidar(port="/dev/ttyUSB0")
scan = await lidar.scan()
obstacles = lidar.find_obstacles(scan, min_distance=0.5)</code></pre>
          </div>
        </div>

        <div class="page-card api-content" v-else>
          <el-empty description="请在左侧选择 API 模块查看详细文档">
            <el-button type="primary" @click="activeApi = 'python-core'">查看核心 API</el-button>
          </el-empty>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Coin, Cpu, Connection } from '@element-plus/icons-vue'

const activeApi = ref('python-core')

const handleApiSelect = (index: string) => {
  activeApi.value = index
}

const coreApiTable = [
  { method: 'connect(host, port)', desc: '连接到指定地址的机器人', returns: 'bool' },
  { method: 'disconnect()', desc: '断开与机器人的连接', returns: 'None' },
  { method: 'get_status()', desc: '获取机器人完整状态信息', returns: 'RobotStatus' },
  { method: 'set_mode(mode)', desc: '设置运行模式（auto/manual/remote/safe）', returns: 'None' },
  { method: 'enable_safety()', desc: '启用安全监护功能', returns: 'None' },
  { method: 'shutdown()', desc: '安全关闭机器人系统', returns: 'None' },
  { method: 'reboot()', desc: '重启机器人机载系统', returns: 'None' },
  { method: 'is_connected()', desc: '检查连接状态', returns: 'bool' },
]

const statusFields = [
  { field: 'battery', type: 'float', desc: '电池电量百分比 (0-100)' },
  { field: 'temperature', type: 'float', desc: '核心温度 (°C)' },
  { field: 'mode', type: 'str', desc: '当前运行模式' },
  { field: 'uptime', type: 'int', desc: '系统运行时间（秒）' },
  { field: 'joint_states', type: 'dict', desc: '各关节位置/速度/力矩' },
  { field: 'safety_status', type: 'str', desc: '安全状态 (ok/warning/critical)' },
]
</script>

<style lang="scss" scoped>
.api-sidebar {
  padding: 0;
  overflow: hidden;
  position: sticky;
  top: 24px;
}
.api-content {
  h2 { font-size: 22px; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
  h3 { font-size: 17px; margin: 20px 0 10px; color: var(--qoo-text); }
  .api-desc { color: var(--qoo-text-secondary); margin-bottom: 16px; }
}
.api-example {
  background: #1e1e2e;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  pre { margin: 0; }
  code { color: #cdd6f4; font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; line-height: 1.6; }
}
</style>
