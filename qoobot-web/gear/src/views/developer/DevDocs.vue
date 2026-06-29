<template>
  <div class="dev-docs">
    <h2>开发文档</h2>
    <p class="subtitle">MFQ 配件开发完整指南：从入门到认证</p>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <el-tree
            :data="docTree"
            node-key="id"
            default-expand-all
            :props="{ children: 'children', label: 'label' }"
            @node-click="handleNodeClick"
            highlight-current
          >
            <template #default="{ data }">
              <span class="tree-node">
                <el-icon v-if="data.children" style="margin-right: 6px"><Folder /></el-icon>
                <el-icon v-else style="margin-right: 6px"><Document /></el-icon>
                <span>{{ data.label }}</span>
                <el-tag v-if="data.tag" size="small" :type="data.tagType" style="margin-left: 8px">{{ data.tag }}</el-tag>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card v-if="selectedDoc">
          <template #header>
            <span>{{ selectedDoc.label }}</span>
          </template>
          <div class="doc-preview">
            <p v-if="selectedDoc.summary">{{ selectedDoc.summary }}</p>
            <el-divider />
            <el-button type="primary" size="small" @click="readDoc(selectedDoc)">
              <el-icon><Reading /></el-icon> 阅读全文
            </el-button>
            <el-button size="small" @click="downloadDoc(selectedDoc)">
              <el-icon><Download /></el-icon> 下载PDF
            </el-button>
          </div>
        </el-card>
        <el-card v-else style="margin-top: 0">
          <el-empty description="点击左侧文档节点查看详情" :image-size="80" />
        </el-card>

        <!-- Quick Links -->
        <el-card style="margin-top: 16px">
          <template #header>快速链接</template>
          <div class="quick-links">
            <el-link type="primary" :underline="false" @click="$router.push('/developer/sdk')">SDK 下载</el-link>
            <el-link type="primary" :underline="false" @click="$router.push('/developer/references')">参考设计</el-link>
            <el-link type="primary" :underline="false" @click="$router.push('/developer/self-check')">认证自查</el-link>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Folder, Document, Reading, Download } from '@element-plus/icons-vue'

const selectedDoc = ref<any>(null)

const docTree = ref([
  {
    id: '1', label: '快速入门',
    children: [
      { id: '1-1', label: '环境搭建', summary: '安装 qoogear-sdk、配置开发环境、连接 QooBot 模拟器', tag: '必读', tagType: 'danger' },
      { id: '1-2', label: '第一个配件驱动', summary: '从零创建 Gripper 配件驱动，实现基本控制功能' },
      { id: '1-3', label: '运行认证自检', summary: '使用 SelfCheckRunner 进行预认证检查' }
    ]
  },
  {
    id: '2', label: '配件开发',
    children: [
      { id: '2-1', label: '末端执行器开发', summary: 'Gripper 机械/电气/通信接口开发指南', tag: '热门', tagType: 'warning' },
      { id: '2-2', label: '传感器模组开发', summary: '传感器数据采集、时间同步、CAN-FD 上报' },
      { id: '2-3', label: '电源配件开发', summary: '充电管理、电池状态上报、安全保护机制' },
      { id: '2-4', label: '可穿戴外设开发', summary: 'BLE 通信、触觉反馈、手势识别集成' }
    ]
  },
  {
    id: '3', label: '认证指南',
    children: [
      { id: '3-1', label: 'MFQ 认证流程', summary: '完整认证流程：申请→审核→测试→发证', tag: '重要', tagType: 'danger' },
      { id: '3-2', label: '认证自查清单', summary: '提交认证前的自检项目完整清单' },
      { id: '3-3', label: '常见问题 FAQ', summary: '认证过程中常见问题及解决方案' }
    ]
  },
  {
    id: '4', label: 'API 参考',
    children: [
      { id: '4-1', label: 'Python SDK API', summary: 'qoogear-sdk Python API 完整参考' },
      { id: '4-2', label: 'C++ SDK API', summary: 'qoogear-sdk C++ API 完整参考' },
      { id: '4-3', label: 'Protobuf 协议', summary: 'peripheral.proto / certification.proto 协议文档' },
      { id: '4-4', label: 'REST API', summary: 'qoogear-cloud 服务端 REST API 文档' }
    ]
  },
  {
    id: '5', label: '最佳实践',
    children: [
      { id: '5-1', label: '配件安全设计', summary: '硬件安全、固件签名、通信加密最佳实践' },
      { id: '5-2', label: '性能优化', summary: 'CAN-FD 带宽优化、传感器采样率调优' },
      { id: '5-3', label: '量产准备', summary: '认证芯片烧录、批量生产流程、质量控制' }
    ]
  }
])

function handleNodeClick(data: any) {
  if (!data.children) {
    selectedDoc.value = data
  }
}

function readDoc(doc: any) {
  ElMessage.info(`正在加载文档：${doc.label}`)
}

function downloadDoc(doc: any) {
  ElMessage.success(`正在下载：${doc.label}.pdf`)
}
</script>

<style scoped>
.dev-docs { padding: 20px; }
.subtitle { color: #909399; margin-bottom: 24px; }
.tree-node { display: flex; align-items: center; font-size: 14px; }
.doc-preview p { color: #606266; line-height: 1.6; }
.quick-links { display: flex; flex-direction: column; gap: 8px; }
</style>
