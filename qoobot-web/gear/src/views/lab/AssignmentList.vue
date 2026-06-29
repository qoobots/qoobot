<template>
  <div class="assignment-list">
    <div class="header">
      <h2>测试任务列表</h2>
      <div class="filters">
        <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 160px" @change="loadAssignments">
          <el-option label="全部" value="" />
          <el-option label="待处理" value="pending" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已完成" value="completed" />
          <el-option label="已驳回" value="rejected" />
        </el-select>
        <el-select v-model="filterLevel" placeholder="认证等级" clearable style="width: 140px; margin-left: 12px" @change="loadAssignments">
          <el-option label="全部" value="" />
          <el-option label="Basic" value="basic" />
          <el-option label="Premium" value="premium" />
          <el-option label="Pro" value="pro" />
        </el-select>
      </div>
    </div>

    <el-table :data="assignments" stripe v-loading="loading" @sort-change="handleSort">
      <el-table-column prop="applicationId" label="申请编号" width="180" sortable="custom" />
      <el-table-column prop="productName" label="产品名称" />
      <el-table-column prop="productCategory" label="类别" width="120">
        <template #default="{ row }">
          <el-tag>{{ categoryLabel(row.productCategory) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="certLevel" label="认证等级" width="110">
        <template #default="{ row }">
          <CertLevelBadge :level="row.certLevel" />
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="assignedAt" label="分配时间" width="160" sortable="custom" />
      <el-table-column prop="deadline" label="截止日期" width="120" sortable="custom">
        <template #default="{ row }">
          <span :style="{ color: isOverdue(row.deadline) ? 'red' : '' }">{{ row.deadline || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="$router.push(`/lab/assignments/${row.id}`)">详情</el-button>
          <el-button v-if="row.status === 'in_progress'" type="success" size="small" @click="markComplete(row)">完成</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="pageSize"
      layout="total, prev, pager, next"
      @current-change="loadAssignments"
      style="margin-top: 16px"
    />

    <!-- Complete Dialog -->
    <el-dialog v-model="completeDialog.visible" title="标记测试完成" width="500px">
      <p>确认将 <strong>{{ completeDialog.productName }}</strong> 标记为已完成？</p>
      <el-form label-width="100px">
        <el-form-item label="测试结果">
          <el-select v-model="completeDialog.result" style="width: 100%">
            <el-option label="通过" value="pass" />
            <el-option label="有条件通过" value="conditional_pass" />
            <el-option label="不通过" value="fail" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="completeDialog.note" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="completeDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmComplete">确认完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { labApi } from '@/api/developer'
import CertLevelBadge from '@/components/cert/CertLevelBadge.vue'

const loading = ref(false)
const assignments = ref<any[]>([])
const page = ref(1)
const total = ref(0)
const pageSize = 20
const filterStatus = ref('')
const filterLevel = ref('')

const completeDialog = reactive({
  visible: false,
  assignmentId: 0,
  productName: '',
  result: 'pass',
  note: ''
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

function isOverdue(deadline: string): boolean {
  if (!deadline) return false
  return new Date(deadline) < new Date()
}

async function loadAssignments() {
  loading.value = true
  try {
    const params: any = { page: page.value - 1, size: pageSize }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterLevel.value) params.certLevel = filterLevel.value
    const res = await labApi.listAssignments(params)
    assignments.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch {
    // Use sample data for development
    assignments.value = [
      { id: 1, applicationId: 'MFQ-2026-0003', productName: 'QooGrip Pro', productCategory: 'gripper', certLevel: 'premium', status: 'in_progress', assignedAt: '2026-06-15', deadline: '2026-07-15' },
      { id: 2, applicationId: 'MFQ-2026-0008', productName: 'QooSense Mini', productCategory: 'sensor', certLevel: 'basic', status: 'completed', assignedAt: '2026-05-20', deadline: '2026-06-20' },
      { id: 3, applicationId: 'MFQ-2026-0012', productName: 'PowerCell X1', productCategory: 'power', certLevel: 'premium', status: 'pending', assignedAt: '2026-06-28', deadline: '2026-07-28' }
    ]
    total.value = 3
  } finally {
    loading.value = false
  }
}

function handleSort(sort: any) {
  loadAssignments()
}

function markComplete(row: any) {
  completeDialog.assignmentId = row.id
  completeDialog.productName = row.productName
  completeDialog.result = 'pass'
  completeDialog.note = ''
  completeDialog.visible = true
}

async function confirmComplete() {
  try {
    await labApi.submitResults(completeDialog.assignmentId, {
      result: completeDialog.result,
      note: completeDialog.note
    })
    ElMessage.success('测试已完成')
    completeDialog.visible = false
    loadAssignments()
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(() => loadAssignments())
</script>

<style scoped>
.assignment-list { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { margin: 0; }
.filters { display: flex; }
</style>
