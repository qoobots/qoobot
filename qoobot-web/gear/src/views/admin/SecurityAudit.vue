<template>
  <div class="security-audit">
    <h2>安全审计</h2>

    <div class="stats-row">
      <el-statistic-card title="总审计数" :value="audits.length" />
      <el-statistic-card title="高风险" :value="highRiskCount" color="#f56c6c" />
      <el-statistic-card title="中风险" :value="mediumRiskCount" color="#e6a23c" />
      <el-statistic-card title="低风险" :value="lowRiskCount" color="#67c23a" />
    </div>

    <el-table :data="audits" stripe v-loading="loading" style="margin-top: 20px">
      <el-table-column prop="applicationId" label="申请编号" width="180" />
      <el-table-column prop="productName" label="产品名称" />
      <el-table-column prop="riskLevel" label="风险等级" width="110">
        <template #default="{ row }">
          <el-tag :type="riskTagType(row.riskLevel)">{{ riskLabel(row.riskLevel) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="auditor" label="审计员" width="120" />
      <el-table-column prop="findings" label="审计发现" show-overflow-tooltip />
      <el-table-column prop="createdAt" label="审计时间" width="160" sortable="custom" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" link @click="viewAudit(row)">查看</el-button>
          <el-button type="warning" size="small" link @click="viewFmea(row)">FMEA</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Audit Detail -->
    <el-dialog v-model="auditDialog.visible" title="审计详情" width="700px">
      <template v-if="auditDialog.audit">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="申请编号">{{ auditDialog.audit.applicationId }}</el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="riskTagType(auditDialog.audit.riskLevel)">{{ riskLabel(auditDialog.audit.riskLevel) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="审计员">{{ auditDialog.audit.auditor }}</el-descriptions-item>
          <el-descriptions-item label="审计时间">{{ auditDialog.audit.createdAt }}</el-descriptions-item>
          <el-descriptions-item label="审计发现" :span="2">{{ auditDialog.audit.findings }}</el-descriptions-item>
          <el-descriptions-item label="建议措施" :span="2">{{ auditDialog.audit.recommendation || '无' }}</el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>

    <!-- FMEA Dialog -->
    <el-dialog v-model="fmeaDialog.visible" title="FMEA 分析" width="800px">
      <el-table :data="fmeaItems" stripe size="small">
        <el-table-column prop="failureMode" label="失效模式" width="200" />
        <el-table-column prop="effect" label="影响" />
        <el-table-column prop="severity" label="严重度" width="80">
          <template #default="{ row }">
            <el-tag :type="severityTagType(row.severity)">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="occurrence" label="发生频率" width="90" />
        <el-table-column prop="detection" label="检测度" width="80" />
        <el-table-column prop="rpn" label="RPN" width="80">
          <template #default="{ row }">
            <span :style="{ color: row.rpn > 100 ? '#f56c6c' : row.rpn > 50 ? '#e6a23c' : '#67c23a', fontWeight: 'bold' }">
              {{ row.rpn }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'

const loading = ref(false)
const audits = ref<any[]>([])

const auditDialog = reactive({ visible: false, audit: null as any })
const fmeaDialog = reactive({ visible: false, fmeaItems: [] as any[] })

const highRiskCount = computed(() => audits.value.filter(a => a.riskLevel === 'high' || a.riskLevel === 'critical').length)
const mediumRiskCount = computed(() => audits.value.filter(a => a.riskLevel === 'medium').length)
const lowRiskCount = computed(() => audits.value.filter(a => a.riskLevel === 'low').length)

function riskTagType(level: string): string {
  const map: Record<string, string> = { low: 'success', medium: 'warning', high: 'danger', critical: 'danger' }
  return map[level] || 'info'
}

function riskLabel(level: string): string {
  const map: Record<string, string> = { low: '低', medium: '中', high: '高', critical: '严重' }
  return map[level] || level
}

function severityTagType(severity: number): string {
  if (severity >= 8) return 'danger'
  if (severity >= 5) return 'warning'
  return 'success'
}

async function loadAudits() {
  loading.value = true
  try {
    audits.value = [
      { id: 1, applicationId: 'MFQ-2026-0015', productName: 'DexHand Pro', riskLevel: 'medium', auditor: 'Li Wei', findings: 'CAN-FD通信中断恢复时间超出标准要求，建议增加看门狗机制', recommendation: '增加通信超时自动重连功能', createdAt: '2026-06-29' },
      { id: 2, applicationId: 'MFQ-2026-0010', productName: 'QooSense Vision', riskLevel: 'low', auditor: 'Zhang San', findings: '固件签名验证机制符合MFQ标准，无安全缺陷', recommendation: '无', createdAt: '2026-06-20' },
      { id: 3, applicationId: 'MFQ-2026-0005', productName: 'PowerCell Pro', riskLevel: 'high', auditor: 'Wang Wu', findings: '过温保护响应时间超标200ms，存在热失控风险', recommendation: '更换温度传感器型号，优化保护电路', createdAt: '2026-06-25' }
    ]
  } finally {
    loading.value = false
  }
}

function viewAudit(row: any) {
  auditDialog.audit = row
  auditDialog.visible = true
}

function viewFmea(row: any) {
  fmeaDialog.fmeaItems = [
    { failureMode: '通信中断', effect: '配件失控，可能造成碰撞', severity: 8, occurrence: 3, detection: 4, rpn: 96 },
    { failureMode: '过温保护失效', effect: '配件过热，可能损坏', severity: 7, occurrence: 2, detection: 5, rpn: 70 },
    { failureMode: '固件签名被篡改', effect: '恶意固件注入', severity: 10, occurrence: 1, detection: 8, rpn: 80 },
    { failureMode: '急停信号丢失', effect: '无法紧急停止', severity: 9, occurrence: 2, detection: 6, rpn: 108 }
  ]
  fmeaDialog.visible = true
}

onMounted(() => loadAudits())
</script>

<style scoped>
.security-audit { padding: 20px; }
h2 { margin-bottom: 20px; }
.stats-row { display: flex; gap: 16px; flex-wrap: wrap; }
</style>
