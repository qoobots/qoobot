<template>
  <div class="assignment-detail">
    <el-page-header @back="$router.back()" title="返回任务列表" />

    <el-card style="margin-top: 20px" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>测试任务 — {{ assignment?.applicationId }}</span>
          <el-tag v-if="assignment" :type="statusTagType(assignment.status)">
            {{ statusLabel(assignment.status) }}
          </el-tag>
        </div>
      </template>

      <el-descriptions :column="2" border v-if="assignment">
        <el-descriptions-item label="产品名称">{{ assignment.productName }}</el-descriptions-item>
        <el-descriptions-item label="认证等级">
          <CertLevelBadge :level="assignment.certLevel" />
        </el-descriptions-item>
        <el-descriptions-item label="产品类别">
          <el-tag>{{ categoryLabel(assignment.productCategory) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="产品型号">{{ assignment.productModel || '-' }}</el-descriptions-item>
        <el-descriptions-item label="分配时间">{{ assignment.assignedAt }}</el-descriptions-item>
        <el-descriptions-item label="截止日期">
          <span :style="{ color: isOverdue ? 'red' : '' }">{{ assignment.deadline || '-' }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="对应标准" :span="2">
          {{ assignment.standardRef || 'MFQ-GRIPPER-V2.0' }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- Test Checklist -->
      <div style="margin-top: 24px">
        <h4>测试项目清单</h4>
        <el-checkbox-group v-model="checkedItems" :disabled="assignment?.status === 'completed'">
          <el-checkbox
            v-for="item in testItems"
            :key="item.id"
            :label="item.id"
            style="display: block; margin-bottom: 10px"
          >
            <span class="test-item-label">{{ item.name }}</span>
            <el-tag size="small" :type="item.required ? 'danger' : 'info'" style="margin-left: 8px">
              {{ item.required ? '必测' : '选测' }}
            </el-tag>
            <span class="test-item-desc"> — {{ item.description }}</span>
          </el-checkbox>
        </el-checkbox-group>
      </div>

      <!-- Test Results Section -->
      <div style="margin-top: 24px" v-if="testResults.length > 0">
        <h4>已提交的测试结果</h4>
        <el-table :data="testResults" stripe size="small">
          <el-table-column prop="testItem" label="测试项目" />
          <el-table-column prop="result" label="结果" width="120">
            <template #default="{ row }">
              <el-tag :type="resultTagType(row.result)">{{ resultLabel(row.result) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="measuredValue" label="实测值" width="150" />
          <el-table-column prop="specValue" label="规格要求" width="150" />
          <el-table-column prop="submittedAt" label="提交时间" width="160" />
        </el-table>
      </div>

      <!-- Actions -->
      <div style="margin-top: 24px" v-if="assignment?.status !== 'completed'">
        <el-button type="primary" @click="showSubmitDialog">提交测试报告</el-button>
        <el-button type="success" @click="showCompleteDialog" :disabled="checkedItems.length < requiredCount">
          标记完成 ({{ checkedItems.length }}/{{ testItems.length }})
        </el-button>
      </div>
    </el-card>

    <!-- Submit Report Dialog -->
    <el-dialog v-model="submitDialog.visible" title="提交测试结果" width="600px">
      <el-form :model="submitDialog.form" label-width="100px">
        <el-form-item label="测试项目">
          <el-select v-model="submitDialog.form.testItem" style="width: 100%">
            <el-option v-for="item in uncheckedItems" :key="item.id" :label="item.name" :value="item.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试结果">
          <el-select v-model="submitDialog.form.result" style="width: 100%">
            <el-option label="通过" value="pass" />
            <el-option label="有条件通过" value="conditional_pass" />
            <el-option label="不通过" value="fail" />
          </el-select>
        </el-form-item>
        <el-form-item label="实测值">
          <el-input v-model="submitDialog.form.measuredValue" placeholder="如：25.4mm" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="submitDialog.form.note" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="submitDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitResult">提交</el-button>
      </template>
    </el-dialog>

    <!-- Complete Dialog -->
    <el-dialog v-model="completeDialog.visible" title="确认完成" width="450px">
      <p>确认所有测试项目已完成？完成后将通知审核人员。</p>
      <el-input v-model="completeDialog.summary" type="textarea" :rows="3" placeholder="测试总结（可选）" />
      <template #footer>
        <el-button @click="completeDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmComplete">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { labApi } from '@/api/developer'
import CertLevelBadge from '@/components/cert/CertLevelBadge.vue'

const route = useRoute()
const loading = ref(false)
const assignment = ref<any>(null)
const checkedItems = ref<number[]>([])
const testResults = ref<any[]>([])

const testItems = ref([
  { id: 1, name: '机械配合精度测试', description: '验证与QooBot机械接口配合公差', required: true },
  { id: 2, name: '电气接口兼容性测试', description: '验证电源/信号引脚定义兼容性', required: true },
  { id: 3, name: 'CAN-FD通信协议测试', description: '验证CAN-FD帧格式和波特率匹配', required: true },
  { id: 4, name: '急停联动测试', description: '验证急停信号传递延迟 < 10ms', required: true },
  { id: 5, name: '过流保护测试', description: '验证过流保护触发阈值', required: true },
  { id: 6, name: '过温保护测试', description: '验证过温保护触发温度', required: false },
  { id: 7, name: '耐久性测试', description: '10000次循环无故障', required: false },
  { id: 8, name: 'EMC电磁兼容测试', description: '验证辐射/传导发射限值', required: false }
])

const requiredCount = computed(() => testItems.value.filter(t => t.required).length)
const uncheckedItems = computed(() => testItems.value.filter(t => !checkedItems.value.includes(t.id)))
const isOverdue = computed(() => assignment.value?.deadline && new Date(assignment.value.deadline) < new Date())

const submitDialog = reactive({
  visible: false,
  form: { testItem: '', result: 'pass', measuredValue: '', note: '' }
})

const completeDialog = reactive({
  visible: false,
  summary: ''
})

function categoryLabel(cat: string): string {
  const map: Record<string, string> = {
    gripper: '末端执行器', sensor: '传感器', wearable: '可穿戴',
    power: '电源', mobility: '移动平台', tool: '工具'
  }
  return map[cat] || cat
}

function statusTagType(status: string): string {
  const map: Record<string, string> = { pending: 'info', in_progress: 'warning', completed: 'success', rejected: 'danger' }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = { pending: '待处理', in_progress: '进行中', completed: '已完成', rejected: '已驳回' }
  return map[status] || status
}

function resultTagType(result: string): string {
  const map: Record<string, string> = { pass: 'success', conditional_pass: 'warning', fail: 'danger' }
  return map[result] || 'info'
}

function resultLabel(result: string): string {
  const map: Record<string, string> = { pass: '通过', conditional_pass: '有条件通过', fail: '不通过' }
  return map[result] || result
}

async function loadAssignment() {
  loading.value = true
  try {
    const id = route.params.id
    // Use sample data for now
    assignment.value = {
      id: Number(id),
      applicationId: 'MFQ-2026-0003',
      productName: 'QooGrip Pro',
      productCategory: 'gripper',
      productModel: 'QGP-V2',
      certLevel: 'premium',
      status: 'in_progress',
      assignedAt: '2026-06-15',
      deadline: '2026-07-15',
      standardRef: 'MFQ-GRIPPER-V2.0'
    }
    testResults.value = [
      { testItem: '机械配合精度测试', result: 'pass', measuredValue: '0.02mm', specValue: '≤ 0.05mm', submittedAt: '2026-06-18' },
      { testItem: '电气接口兼容性测试', result: 'pass', measuredValue: '24V/5A', specValue: '24V/5A', submittedAt: '2026-06-18' }
    ]
    checkedItems.value = [1, 2]
  } catch {
    ElMessage.error('加载任务详情失败')
  } finally {
    loading.value = false
  }
}

function showSubmitDialog() {
  if (uncheckedItems.value.length === 0) {
    ElMessage.warning('所有测试项目已提交')
    return
  }
  submitDialog.form = { testItem: uncheckedItems.value[0].name, result: 'pass', measuredValue: '', note: '' }
  submitDialog.visible = true
}

function submitResult() {
  testResults.value.push({
    testItem: submitDialog.form.testItem,
    result: submitDialog.form.result,
    measuredValue: submitDialog.form.measuredValue,
    specValue: '-',
    submittedAt: new Date().toISOString().split('T')[0]
  })
  const item = testItems.value.find(t => t.name === submitDialog.form.testItem)
  if (item && !checkedItems.value.includes(item.id)) {
    checkedItems.value.push(item.id)
  }
  submitDialog.visible = false
  ElMessage.success('测试结果已提交')
}

function showCompleteDialog() {
  completeDialog.summary = ''
  completeDialog.visible = true
}

async function confirmComplete() {
  try {
    assignment.value.status = 'completed'
    completeDialog.visible = false
    ElMessage.success('测试任务已完成')
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(() => loadAssignment())
</script>

<style scoped>
.assignment-detail { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.test-item-label { font-weight: 500; }
.test-item-desc { color: #909399; font-size: 13px; }
h4 { margin-bottom: 12px; }
</style>
