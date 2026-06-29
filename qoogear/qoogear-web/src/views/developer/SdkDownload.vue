<template>
  <div class="sdk-download">
    <h2>SDK 下载</h2>
    <p class="desc">QooBot MFQ 配件开发工具包</p>
    <el-row :gutter="24">
      <el-col :span="8" v-for="sdk in sdks" :key="sdk.platform">
        <el-card class="sdk-card">
          <div class="sdk-icon">
            <el-icon :size="48"><component :is="sdk.icon" /></el-icon>
          </div>
          <h3>{{ sdk.name }}</h3>
          <p>{{ sdk.description }}</p>
          <el-tag size="small">{{ sdk.language }}</el-tag>
          <div class="sdk-version">v{{ sdk.version }} · {{ sdk.releasedAt }}</div>
          <el-button type="primary" style="width: 100%; margin-top: 16px">
            <el-icon><Download /></el-icon> 下载
          </el-button>
          <el-button link style="width: 100%; margin-top: 8px" @click="showReleaseNotes(sdk)">
            查看发布说明
          </el-button>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="quick-start">
      <template #header>快速开始</template>
      <el-tabs>
        <el-tab-pane label="Python">
          <pre class="code-block"><code>pip install qoogear-sdk
qoogear init my-gripper
qoogear test
qoogear simulate gripper</code></pre>
        </el-tab-pane>
        <el-tab-pane label="C++">
          <pre class="code-block"><code>git clone https://github.com/qoobot/qoogear-sdk.git
cd qoogear-sdk/cpp && mkdir build && cd build
cmake .. && make -j$(nproc)</code></pre>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const sdks = [
  { platform: 'python', name: 'Python SDK', language: 'Python 3.9+', icon: 'Promotion', description: '配件驱动开发框架、通信协议库、自检套件、模拟器', version: '1.0.0', releasedAt: '2026-06-01' },
  { platform: 'cpp', name: 'C++ SDK', language: 'C++17', icon: 'Cpu', description: '嵌入式/实时配件驱动、CAN/EtherCAT通信、硬件安全', version: '1.0.0', releasedAt: '2026-06-01' },
  { platform: 'proto', name: 'Protobuf 协议', language: 'Protocol Buffers', icon: 'Connection', description: '配件能力声明、控制指令、状态上报消息定义', version: '1.0.0', releasedAt: '2026-06-01' },
]

function showReleaseNotes(sdk: any) {
  ElMessage.info(`v${sdk.version}: Initial MFQ certification support`)
}
</script>

<style scoped>
.desc { color: #909399; margin-bottom: 24px; }
.sdk-card { text-align: center; padding: 20px; margin-bottom: 20px; }
.sdk-icon { margin-bottom: 16px; color: #409eff; }
.sdk-card h3 { margin-bottom: 8px; }
.sdk-card p { color: #606266; font-size: 13px; margin-bottom: 12px; }
.sdk-version { color: #c0c4cc; font-size: 12px; margin-top: 8px; }
.quick-start { margin-top: 24px; }
.code-block { background: #f5f7fa; padding: 16px; border-radius: 4px; font-size: 13px; overflow-x: auto; }
</style>
