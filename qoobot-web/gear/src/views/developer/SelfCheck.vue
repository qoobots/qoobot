<template>
  <div class="self-check">
    <h2>认证自查</h2>
    <p class="subtitle">运行 MFQ 认证预测试，确认配件符合规范要求后再提交正式认证</p>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>
            <span>检查项目</span>
            <el-tag v-if="lastRunAt" size="small" style="margin-left: 12px">
              上次运行：{{ lastRunAt }}
            </el-tag>
          </template>

          <div v-for="category in categories" :key="category.key" class="check-category">
            <h4 class="category-title">
              <el-icon><component :is="category.icon" /></el-icon>
              {{ category.label }}
              <el-tag size="small" style="margin-left: 8px">
                {{ checkedCount(category.key) }}/{{ category.items.length }}
              </el-tag>
            </h4>
            <el-checkbox-group v-model="checkedItems" :disabled="isRunning">
              <el-checkbox
                v-for="item in category.items"
                :key="item.id"
                :label="item.id"
                :disabled="isRunning"
                style="display: block; margin-bottom: 10px; padding: 8px 12px; background: #fafafa; border-radius: 6px"
              >
                <div class="check-item">
                  <span class="check-name">{{ item.name }}</span>
                  <span class="check-desc">{{ item.description }}</span>
                </div>
                <el-tag v-if="checkResults[item.id]" size="small" :type="checkResults[item.id] === 'pass' ? 'success' : 'danger'" style="margin-left: 12px">
                  {{ checkResults[item.id] === 'pass' ? '✓ 通过' : '✗ 未通过' }}
                </el-tag>
              </el-checkbox>
            </el-checkbox-group>
          </div>

          <div class="actions">
            <el-button
              type="primary"
              size="large"
              @click="runCheck"
              :loading="isRunning"
              :disabled="checkedItems.length === 0"
            >
              <el-icon><CaretRight /></el-icon> {{ isRunning ? '运行中...' : '运行自查' }}
            </el-button>
            <el-button size="large" @click="resetCheck" :disabled="isRunning">重置</el-button>
          </div>

          <!-- Results Summary -->
          <div v-if="showResults" style="margin-top: 24px">
            <el-alert
              :title="resultSummary"
              :type="overallPass ? 'success' : 'warning'"
              :closable="false"
              show-icon
            >
              <template #default>
                <p>{{ resultDetail }}</p>
                <div class="result-stats">
                  <el-tag type="success">通过 {{ passCount }}</el-tag>
                  <el-tag type="danger" style="margin-left: 8px">未通过 {{ failCount }}</el-tag>
                  <el-tag type="info" style="margin-left: 8px">未检查 {{ uncheckedCount }}</el-tag>
                </div>
                <div v-if="overallPass" style="margin-top: 12px">
                  <el-button type="success" @click="$router.push('/developer/applications/create')">
                    提交认证申请
                  </el-button>
                </div>
              </template>
            </el-alert>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>自查指南</template>
          <el-steps direction="vertical" :active="stepActive">
            <el-step title="选择检查项" description="勾选需要检查的项目" />
            <el-step title="连接配件" description="确保配件已连接并上电" />
            <el-step title="运行自查" description="点击运行自查按钮" />
            <el-step title="查看结果" description="通过后可提交认证申请" />
          </el-steps>
        </el-card>

        <el-card style="margin-top: 16px">
          <template #header>检查统计</template>
          <div class="stats-grid">
            <div class="stat-box pass">
              <div class="stat-num">{{ passCount }}</div>
              <div class="stat-label">通过</div>
            </div>
            <div class="stat-box fail">
              <div class="stat-num">{{ failCount }}</div>
              <div class="stat-label">未通过</div>
            </div>
            <div class="stat-box total">
              <div class="stat-num">{{ totalChecks }}</div>
              <div class="stat-label">总项目</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { CaretRight, Setting, Connection, Warning, Monitor } from '@element-plus/icons-vue'

const isRunning = ref(false)
const showResults = ref(false)
const checkedItems = ref<string[]>([])
const checkResults = ref<Record<string, string>>({})
const lastRunAt = ref('')

const categories = ref([
  {
    key: 'mechanical', label: '机械接口', icon: markRaw(Setting),
    items: [
      { id: 'mech_connector', name: '机械连接器配合', description: '验证法兰面平面度 ≤ 0.05mm，定位销配合间隙 ≤ 0.02mm' },
      { id: 'mech_load', name: '额定负载测试', description: '在额定负载下无塑性变形，位移 ≤ 0.1mm' },
      { id: 'mech_durability', name: '耐久性测试', description: '1000次插拔循环后配合精度保持' }
    ]
  },
  {
    key: 'electrical', label: '电气接口', icon: markRaw(Connection),
    items: [
      { id: 'elec_voltage', name: '供电电压范围', description: '18V-30V DC 范围内正常工作' },
      { id: 'elec_current', name: '额定电流', description: '持续电流 ≤ 5A，峰值电流 ≤ 10A (1s)' },
      { id: 'elec_protection', name: '保护功能', description: '过流/过压/反接保护正常触发' }
    ]
  },
  {
    key: 'protocol', label: '通信协议', icon: markRaw(Monitor),
    items: [
      { id: 'proto_handshake', name: '协议握手', description: 'CAN-FD 握手在 100ms 内完成' },
      { id: 'proto_heartbeat', name: '心跳机制', description: '心跳间隔 ≤ 100ms，超时检测正常' },
      { id: 'proto_data', name: '数据传输', description: '数据帧格式正确，CRC 校验通过' }
    ]
  },
  {
    key: 'safety', label: '安全功能', icon: markRaw(Warning),
    items: [
      { id: 'safety_estop', name: '急停功能', description: '急停信号延迟 ≤ 10ms' },
      { id: 'safety_overtemp', name: '过温保护', description: '温度 ≥ 85°C 时自动停止' },
      { id: 'safety_watchdog', name: '看门狗', description: '通信中断 500ms 内进入安全状态' }
    ]
  }
])

const totalChecks = computed(() => categories.value.reduce((sum, c) => sum + c.items.length, 0))
const passCount = computed(() => Object.values(checkResults.value).filter(r => r === 'pass').length)
const failCount = computed(() => Object.values(checkResults.value).filter(r => r === 'fail').length)
const uncheckedCount = computed(() => totalChecks.value - passCount.value - failCount.value)
const overallPass = computed(() => failCount.value === 0 && passCount.value > 0)

const resultSummary = computed(() => {
  if (!showResults.value) return ''
  return overallPass.value ? '✅ 自查通过 — 所有检查项均符合 MFQ 规范要求' : '⚠️ 存在未通过项 — 请修复后重新运行'
})

const resultDetail = computed(() => {
  if (!showResults.value) return ''
  if (overallPass.value) return '您的配件已通过所有选中项目的 MFQ 预认证检查，可以提交正式认证申请。'
  return '部分检查项未通过，请查看详情并修复相关问题。'
})

const stepActive = computed(() => {
  if (showResults.value) return 4
  if (isRunning.value) return 3
  if (checkedItems.value.length > 0) return 2
  return 1
})

function checkedCount(categoryKey: string) {
  const cat = categories.value.find(c => c.key === categoryKey)
  if (!cat) return 0
  return cat.items.filter(i => checkedItems.value.includes(i.id)).length
}

async function runCheck() {
  isRunning.value = true
  showResults.value = false
  checkResults.value = {}

  // Simulate running checks one by one
  for (const itemId of checkedItems.value) {
    await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 400))
    // Simulate 90% pass rate
    checkResults.value[itemId] = Math.random() > 0.1 ? 'pass' : 'fail'
  }

  isRunning.value = false
  showResults.value = true
  lastRunAt.value = new Date().toLocaleString()
}

function resetCheck() {
  checkedItems.value = []
  checkResults.value = {}
  showResults.value = false
}
</script>

<style scoped>
.self-check { padding: 20px; }
.subtitle { color: #909399; margin-bottom: 24px; }
.check-category { margin-bottom: 24px; }
.category-title { display: flex; align-items: center; gap: 6px; margin-bottom: 12px; }
.check-item { display: flex; flex-direction: column; }
.check-name { font-weight: 500; }
.check-desc { font-size: 12px; color: #909399; }
.actions { margin-top: 24px; display: flex; gap: 12px; }
.result-stats { margin-top: 12px; }
.stats-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
.stat-box { text-align: center; padding: 12px; border-radius: 8px; }
.stat-box.pass { background: #f0f9eb; }
.stat-box.fail { background: #fef0f0; }
.stat-box.total { background: #f5f7fa; }
.stat-num { font-size: 24px; font-weight: bold; }
.stat-box.pass .stat-num { color: #67c23a; }
.stat-box.fail .stat-num { color: #f56c6c; }
.stat-box.total .stat-num { color: #409eff; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
</style>
