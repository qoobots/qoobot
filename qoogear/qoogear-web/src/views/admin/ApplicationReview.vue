<template>
  <div class="application-review">
    <h2>申请审核</h2>

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="待审核" name="pending">
        <template #label>
          <span>待审核 <el-badge :value="pendingTotal" :max="99" /></span>
        </template>
        <el-table :data="pendingList" stripe v-loading="loading" @sort-change="handleSortChange">
          <el-table-column prop="applicationId" label="申请编号" width="180" sortable="custom" />
          <el-table-column prop="productName" label="产品名称" />
          <el-table-column prop="productCategory" label="类别" width="120">
            <template #default="{ row }">
              <el-tag>{{ categoryLabel(row.productCategory) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="certLevel" label="认证等级" width="100">
            <template #default="{ row }">
              <CertLevelBadge :level="row.certLevel" />
            </template>
          </el-table-column>
          <el-table-column prop="submittedAt" label="提交时间" width="160" sortable="custom" />
          <el-table-column label="操作" width="240" fixed="right">
            <template #default="{ row }">
              <el-button type="success" size="small" @click="approveApplication(row)">通过</el-button>
              <el-button type="warning" size="small" @click="requestInfo(row)">补充材料</el-button>
              <el-button type="danger" size="small" @click="rejectApplication(row)">驳回</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="pendingPage"
          :total="pendingTotal"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          @current-change="loadPendingList"
          style="margin-top: 16px"
        />
      </el-tab-pane>

      <el-tab-pane label="合规审查" name="compliance">
        <template #label>
          <span>合规审查 <el-badge :value="complianceTotal" :max="99" type="warning" /></span>
        </template>
        <el-table :data="complianceList" stripe v-loading="loading">
          <el-table-column prop="applicationId" label="申请编号" width="180" />
          <el-table-column prop="productName" label="产品名称" />
          <el-table-column prop="productCategory" label="类别" width="120" />
          <el-table-column label="操作" width="280">
            <template #default="{ row }">
              <el-button type="success" size="small" @click="approveCompliance(row)">合规通过</el-button>
              <el-button type="danger" size="small" @click="rejectCompliance(row)">不合规</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="安全审查" name="security">
        <template #label>
          <span>安全审查 <el-badge :value="securityTotal" :max="99" type="danger" /></span>
        </template>
        <el-table :data="securityList" stripe v-loading="loading">
          <el-table-column prop="applicationId" label="申请编号" width="180" />
          <el-table-column prop="productName" label="产品名称" />
          <el-table-column prop="riskLevel" label="风险等级" width="120">
            <template #default="{ row }">
              <el-tag :type="riskTagType(row.riskLevel)">{{ row.riskLevel }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280">
            <template #default="{ row }">
              <el-button type="success" size="small" @click="approveSecurity(row)">安全通过</el-button>
              <el-button type="danger" size="small" @click="rejectSecurity(row)">拒绝</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="已审核" name="reviewed">
        <el-table :data="reviewedList" stripe v-loading="loading">
          <el-table-column prop="applicationId" label="申请编号" width="180" />
          <el-table-column prop="productName" label="产品名称" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <CertStatusTag :status="row.status" />
            </template>
          </el-table-column>
          <el-table-column prop="reviewedAt" label="审核时间" width="160" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button type="primary" size="small" link @click="viewDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="reviewedPage"
          :total="reviewedTotal"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          @current-change="loadReviewedList"
          style="margin-top: 16px"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- Approve Dialog -->
    <el-dialog v-model="approveDialog.visible" :title="approveDialog.title" width="500px">
      <el-form :model="approveDialog.form" label-width="100px">
        <el-form-item label="审核意见">
          <el-input v-model="approveDialog.form.comment" type="textarea" :rows="3" placeholder="输入审核意见（可选）" />
        </el-form-item>
        <el-form-item label="分配实验室" v-if="approveDialog.showLabAssign">
          <el-select v-model="approveDialog.form.labId" placeholder="选择实验室" style="width: 100%">
            <el-option v-for="lab in labOptions" :key="lab.id" :label="lab.name" :value="lab.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmApprove">确认</el-button>
      </template>
    </el-dialog>

    <!-- Reject Dialog -->
    <el-dialog v-model="rejectDialog.visible" title="驳回申请" width="500px">
      <el-form :model="rejectDialog.form" label-width="100px">
        <el-form-item label="驳回原因" required>
          <el-input v-model="rejectDialog.form.reason" type="textarea" :rows="3" placeholder="请输入驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialog.visible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { certApi } from '@/api/cert'
import CertLevelBadge from '@/components/cert/CertLevelBadge.vue'
import CertStatusTag from '@/components/cert/CertStatusTag.vue'

const activeTab = ref('pending')
const loading = ref(false)
const pageSize = 20

// Pending tab
const pendingList = ref<any[]>([])
const pendingPage = ref(1)
const pendingTotal = ref(0)

// Compliance tab
const complianceList = ref<any[]>([])
const complianceTotal = ref(0)

// Security tab
const securityList = ref<any[]>([])
const securityTotal = ref(0)

// Reviewed tab
const reviewedList = ref<any[]>([])
const reviewedPage = ref(1)
const reviewedTotal = ref(0)

const labOptions = ref<{ id: number; name: string }[]>([])

const approveDialog = reactive({
  visible: false,
  title: '',
  showLabAssign: false,
  currentApp: null as any,
  form: { comment: '', labId: null as number | null }
})

const rejectDialog = reactive({
  visible: false,
  currentApp: null as any,
  form: { reason: '' }
})

function categoryLabel(cat: string): string {
  const map: Record<string, string> = {
    gripper: '末端执行器', sensor: '传感器', wearable: '可穿戴',
    power: '电源', mobility: '移动平台', tool: '工具'
  }
  return map[cat] || cat
}

function riskTagType(level: string): string {
  const map: Record<string, string> = { low: 'success', medium: 'warning', high: 'danger', critical: 'danger' }
  return map[level] || 'info'
}

async function loadPendingList() {
  loading.value = true
  try {
    const res = await certApi.listApplications({ status: 'submitted', page: pendingPage.value - 1, size: pageSize })
    pendingList.value = res.data?.items || []
    pendingTotal.value = res.data?.total || 0
  } catch {
    ElMessage.error('加载待审核列表失败')
  } finally {
    loading.value = false
  }
}

async function loadComplianceList() {
  try {
    const res = await certApi.listApplications({ status: 'compliance_check', page: 0, size: 100 })
    complianceList.value = res.data?.items || []
    complianceTotal.value = res.data?.total || 0
  } catch { /* silent */ }
}

async function loadSecurityList() {
  try {
    const res = await certApi.listApplications({ status: 'security_review', page: 0, size: 100 })
    securityList.value = res.data?.items || []
    securityTotal.value = res.data?.total || 0
  } catch { /* silent */ }
}

async function loadReviewedList() {
  try {
    const res = await certApi.listApplications({ status: 'reviewed', page: reviewedPage.value - 1, size: pageSize })
    reviewedList.value = res.data?.items || []
    reviewedTotal.value = res.data?.total || 0
  } catch { /* silent */ }
}

async function loadLabs() {
  try {
    const res = await certApi.listLabs()
    labOptions.value = res.data || []
  } catch { /* silent */ }
}

function handleTabChange(tab: string) {
  if (tab === 'compliance') loadComplianceList()
  else if (tab === 'security') loadSecurityList()
  else if (tab === 'reviewed') loadReviewedList()
}

function handleSortChange(sort: any) {
  // Re-fetch with sort params
  loadPendingList()
}

function approveApplication(row: any) {
  approveDialog.currentApp = row
  approveDialog.title = '审核通过 — ' + row.productName
  approveDialog.showLabAssign = row.status === 'submitted'
  approveDialog.form = { comment: '', labId: null }
  approveDialog.visible = true
}

function approveCompliance(row: any) {
  approveDialog.currentApp = row
  approveDialog.title = '合规审查通过 — ' + row.productName
  approveDialog.showLabAssign = false
  approveDialog.form = { comment: '', labId: null }
  approveDialog.visible = true
}

function approveSecurity(row: any) {
  approveDialog.currentApp = row
  approveDialog.title = '安全审查通过 — ' + row.productName
  approveDialog.showLabAssign = false
  approveDialog.form = { comment: '', labId: null }
  approveDialog.visible = true
}

async function confirmApprove() {
  if (!approveDialog.currentApp) return
  try {
    await certApi.reviewApplication(approveDialog.currentApp.id, {
      reviewerId: 1, // TODO: get from auth store
      approved: true,
      comment: approveDialog.form.comment
    })
    ElMessage.success('审核通过')
    approveDialog.visible = false
    loadPendingList()
    loadComplianceList()
    loadSecurityList()
  } catch {
    ElMessage.error('审核失败')
  }
}

function rejectApplication(row: any) {
  rejectDialog.currentApp = row
  rejectDialog.form = { reason: '' }
  rejectDialog.visible = true
}

function rejectCompliance(row: any) {
  rejectDialog.currentApp = row
  rejectDialog.form = { reason: '' }
  rejectDialog.visible = true
}

function rejectSecurity(row: any) {
  rejectDialog.currentApp = row
  rejectDialog.form = { reason: '' }
  rejectDialog.visible = true
}

async function confirmReject() {
  if (!rejectDialog.currentApp || !rejectDialog.form.reason.trim()) {
    ElMessage.warning('请输入驳回原因')
    return
  }
  try {
    await certApi.reviewApplication(rejectDialog.currentApp.id, {
      reviewerId: 1,
      approved: false,
      comment: rejectDialog.form.reason
    })
    ElMessage.success('已驳回')
    rejectDialog.visible = false
    loadPendingList()
    loadComplianceList()
    loadSecurityList()
  } catch {
    ElMessage.error('操作失败')
  }
}

function requestInfo(row: any) {
  ElMessageBox.prompt('请输入需要补充的材料说明', '补充材料', {
    confirmButtonText: '发送',
    cancelButtonText: '取消'
  }).then(async ({ value }) => {
    // TODO: send request-info notification
    ElMessage.success('已发送补充材料请求')
  }).catch(() => {})
}

function viewDetail(row: any) {
  // Navigate to detail
}

onMounted(() => {
  loadPendingList()
  loadLabs()
})
</script>

<style scoped>
.application-review { padding: 20px; }
h2 { margin-bottom: 20px; }
</style>
