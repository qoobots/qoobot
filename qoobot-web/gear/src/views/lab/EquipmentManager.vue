<template>
  <div class="equipment-manager">
    <div class="header">
      <h2>设备管理</h2>
      <div class="actions">
        <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px" @change="loadEquipment">
          <el-option label="全部" value="" />
          <el-option label="正常" value="normal" />
          <el-option label="需校准" value="warning" />
          <el-option label="故障" value="fault" />
        </el-select>
        <el-button type="primary" style="margin-left: 12px" @click="showAddDialog">
          <el-icon><Plus /></el-icon> 添加设备
        </el-button>
      </div>
    </div>

    <el-table :data="filteredEquipment" stripe v-loading="loading">
      <el-table-column prop="name" label="设备名称" />
      <el-table-column prop="model" label="型号" width="160" />
      <el-table-column prop="serialNumber" label="序列号" width="160" />
      <el-table-column prop="category" label="类别" width="120">
        <template #default="{ row }">
          <el-tag>{{ row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="calibratedAt" label="上次校准" width="120" sortable="custom" />
      <el-table-column prop="nextCalDue" label="下次校准" width="120" sortable="custom" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="equipStatusType(row)">
            {{ equipStatusLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" link @click="calibrateEquip(row)">校准</el-button>
          <el-button type="danger" size="small" link @click="reportFault(row)">报修</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Add Equipment Dialog -->
    <el-dialog v-model="addDialog.visible" title="添加设备" width="550px">
      <el-form :model="addDialog.form" label-width="100px">
        <el-form-item label="设备名称" required>
          <el-input v-model="addDialog.form.name" />
        </el-form-item>
        <el-form-item label="型号" required>
          <el-input v-model="addDialog.form.model" />
        </el-form-item>
        <el-form-item label="序列号" required>
          <el-input v-model="addDialog.form.serialNumber" />
        </el-form-item>
        <el-form-item label="类别" required>
          <el-select v-model="addDialog.form.category" style="width: 100%">
            <el-option label="测量仪器" value="测量仪器" />
            <el-option label="协议分析仪" value="协议分析仪" />
            <el-option label="环境试验箱" value="环境试验箱" />
            <el-option label="电源/负载" value="电源/负载" />
            <el-option label="力学测试" value="力学测试" />
            <el-option label="EMC测试" value="EMC测试" />
          </el-select>
        </el-form-item>
        <el-form-item label="校准周期(月)" required>
          <el-input-number v-model="addDialog.form.calibrationCycle" :min="1" :max="36" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="addEquipment">添加</el-button>
      </template>
    </el-dialog>

    <!-- Calibrate Dialog -->
    <el-dialog v-model="calibrateDialog.visible" title="校准设备" width="450px">
      <p>设备：<strong>{{ calibrateDialog.equipName }}</strong></p>
      <el-form label-width="100px">
        <el-form-item label="校准日期">
          <el-date-picker v-model="calibrateDialog.calDate" type="date" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="校准结果">
          <el-select v-model="calibrateDialog.result" style="width: 100%">
            <el-option label="合格" value="pass" />
            <el-option label="限用" value="limited" />
            <el-option label="不合格" value="fail" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="calibrateDialog.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="calibrateDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmCalibrate">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const loading = ref(false)
const equipment = ref<any[]>([])
const filterStatus = ref('')

const addDialog = reactive({
  visible: false,
  form: { name: '', model: '', serialNumber: '', category: '', calibrationCycle: 6 }
})

const calibrateDialog = reactive({
  visible: false,
  equipId: 0,
  equipName: '',
  calDate: new Date(),
  result: 'pass',
  note: ''
})

const filteredEquipment = computed(() => {
  if (!filterStatus.value) return equipment.value
  const status = filterStatus.value
  return equipment.value.filter(e => {
    if (status === 'warning') return e.status === 'warning'
    if (status === 'fault') return e.status === 'fault'
    if (status === 'normal') return e.status === 'normal'
    return true
  })
})

function equipStatusType(row: any): string {
  if (row.status === 'fault') return 'danger'
  if (row.status === 'warning') return 'warning'
  return 'success'
}

function equipStatusLabel(row: any): string {
  if (row.status === 'fault') return '故障'
  if (row.status === 'warning') return '需校准'
  return '正常'
}

async function loadEquipment() {
  loading.value = true
  try {
    equipment.value = [
      { id: 1, name: '三坐标测量仪', model: 'Hexagon 564', serialNumber: 'CMM-2024-001', category: '测量仪器', calibratedAt: '2026-03-15', nextCalDue: '2026-09-15', status: 'normal' },
      { id: 2, name: 'CAN协议分析仪', model: 'Vector VN1610', serialNumber: 'CAN-2025-012', category: '协议分析仪', calibratedAt: '2026-01-10', nextCalDue: '2026-07-10', status: 'warning' },
      { id: 3, name: '恒温恒湿试验箱', model: 'ESPEC SH-641', serialNumber: 'ENV-2023-008', category: '环境试验箱', calibratedAt: '2026-02-20', nextCalDue: '2026-08-20', status: 'normal' },
      { id: 4, name: '电子万能试验机', model: 'Instron 5965', serialNumber: 'MECH-2024-003', category: '力学测试', calibratedAt: '2025-12-01', nextCalDue: '2026-06-01', status: 'fault' }
    ]
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  addDialog.form = { name: '', model: '', serialNumber: '', category: '', calibrationCycle: 6 }
  addDialog.visible = true
}

function addEquipment() {
  const now = new Date()
  const nextDue = new Date(now)
  nextDue.setMonth(nextDue.getMonth() + addDialog.form.calibrationCycle)

  equipment.value.push({
    id: Date.now(),
    name: addDialog.form.name,
    model: addDialog.form.model,
    serialNumber: addDialog.form.serialNumber,
    category: addDialog.form.category,
    calibratedAt: now.toISOString().split('T')[0],
    nextCalDue: nextDue.toISOString().split('T')[0],
    status: 'normal'
  })
  addDialog.visible = false
  ElMessage.success('设备已添加')
}

function calibrateEquip(row: any) {
  calibrateDialog.equipId = row.id
  calibrateDialog.equipName = row.name
  calibrateDialog.calDate = new Date()
  calibrateDialog.result = 'pass'
  calibrateDialog.note = ''
  calibrateDialog.visible = true
}

function confirmCalibrate() {
  const equip = equipment.value.find(e => e.id === calibrateDialog.equipId)
  if (equip) {
    equip.calibratedAt = calibrateDialog.calDate.toISOString().split('T')[0]
    const nextDue = new Date(calibrateDialog.calDate)
    nextDue.setMonth(nextDue.getMonth() + 6)
    equip.nextCalDue = nextDue.toISOString().split('T')[0]
    equip.status = calibrateDialog.result === 'fail' ? 'fault' : 'normal'
  }
  calibrateDialog.visible = false
  ElMessage.success('校准记录已更新')
}

function reportFault(row: any) {
  row.status = 'fault'
  ElMessage.warning(`设备 "${row.name}" 已标记为故障`)
}

onMounted(() => loadEquipment())
</script>

<style scoped>
.equipment-manager { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { margin: 0; }
.actions { display: flex; align-items: center; }
</style>
