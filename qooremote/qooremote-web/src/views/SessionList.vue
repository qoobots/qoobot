<template>
  <div class="session-page">
    <div class="page-header">
      <h2>遥控会话列表</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        创建会话
      </el-button>
    </div>

    <el-table :data="sessions" style="width: 100%" v-loading="loading" empty-text="暂无会话记录">
      <el-table-column prop="session_id" label="会话 ID" width="200">
        <template #default="{ row }">
          <code class="mono">{{ row.session_id.slice(0, 12) }}...</code>
        </template>
      </el-table-column>
      <el-table-column prop="robot_id" label="机器人" width="150" />
      <el-table-column prop="operator_name" label="操作员" width="120" />
      <el-table-column prop="control_mode" label="模式" width="100">
        <template #default="{ row }">
          <el-tag :type="row.control_mode === 'TELEOP' ? '' : 'success'" size="small">
            {{ modeMap[row.control_mode] || row.control_mode }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="session_status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.session_status)" size="small">
            {{ statusMap[row.session_status] || row.session_status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="command_count" label="指令数" width="100" />
      <el-table-column prop="avg_latency_ms" label="平均延迟" width="100">
        <template #default="{ row }">
          {{ row.avg_latency_ms }}ms
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString() }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.session_status === 'ACTIVE'" type="primary" link size="small"
                     @click="onJoinSession(row.session_id)">
            加入
          </el-button>
          <el-button v-if="row.session_status !== 'CLOSED'" type="danger" link size="small"
                     @click="onTerminate(row.session_id)">
            终止
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建会话对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建遥控会话" width="480px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="机器人 ID">
          <el-input v-model="createForm.robot_id" placeholder="输入机器人 ID" />
        </el-form-item>
        <el-form-item label="媒体类型">
          <el-checkbox-group v-model="createForm.media_types">
            <el-checkbox label="VIDEO">视频</el-checkbox>
            <el-checkbox label="AUDIO">音频</el-checkbox>
            <el-checkbox label="DATA">数据通道</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="onCreateSession">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTeleopStore } from '@/stores/teleop'
import { sessionApi } from '@/api/teleop'
import type { TeleopSession } from '@/types/teleop'

const router = useRouter()
const store = useTeleopStore()

const sessions = ref<TeleopSession[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)

const createForm = ref({
  robot_id: '',
  media_types: ['VIDEO', 'AUDIO', 'DATA']
})

const modeMap: Record<string, string> = { AUTO: '自主', HYBRID: '混合', TELEOP: '遥控' }
const statusMap: Record<string, string> = {
  INITIATING: '初始化', CONNECTING: '连接中', ACTIVE: '活跃',
  PAUSED: '暂停', CLOSING: '关闭中', CLOSED: '已关闭',
  REJECTED: '已拒绝', TIMEOUT: '超时'
}

function statusType(status: string) {
  return status === 'ACTIVE' ? 'success' : status === 'CLOSED' ? 'info' : 'warning'
}

async function fetchSessions() {
  loading.value = true
  try {
    const { data } = await sessionApi.list()
    if (data.code === 0) sessions.value = data.data || []
  } catch (e) {
    console.error('Failed to fetch sessions:', e)
  } finally {
    loading.value = false
  }
}

async function onCreateSession() {
  const session = await store.createSession(createForm.value.robot_id, 'operator', createForm.value.media_types)
  if (session) {
    showCreateDialog.value = false
    router.push('/')
  }
}

function onJoinSession(sessionId: string) {
  router.push('/')
}

async function onTerminate(sessionId: string) {
  try {
    await sessionApi.terminate(sessionId)
    fetchSessions()
  } catch (e) {
    console.error('Terminate failed:', e)
  }
}

onMounted(fetchSessions)
</script>

<style lang="scss" scoped>
.session-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  h2 {
    font-size: 20px;
    font-weight: 600;
  }
}

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}
</style>
