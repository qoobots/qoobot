<template>
  <div class="certificate-manager">
    <div class="header">
      <h2>证书管理</h2>
      <el-input v-model="searchQuery" placeholder="搜索证书编号/产品/厂商" clearable style="width: 300px" @keyup.enter="search" />
    </div>

    <el-table :data="certs" stripe v-loading="loading" @sort-change="handleSort">
      <el-table-column prop="certNumber" label="证书编号" width="220" sortable="custom" />
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
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row)">
            {{ statusLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="issuedAt" label="签发日期" width="120" sortable="custom" />
      <el-table-column prop="expiresAt" label="过期日期" width="120" sortable="custom" />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" link @click="viewDetail(row)">详情</el-button>
          <el-button type="warning" size="small" link @click="renewCert(row)" :disabled="!row.isActive">续期</el-button>
          <el-button type="danger" size="small" link @click="confirmRevoke(row)" :disabled="!row.isActive">吊销</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="pageSize"
      layout="total, prev, pager, next"
      @current-change="loadCerts"
      style="margin-top: 16px"
    />

    <!-- Detail Dialog -->
    <el-dialog v-model="detailDialog.visible" title="证书详情" width="600px">
      <template v-if="detailDialog.cert">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="证书编号">{{ detailDialog.cert.certNumber }}</el-descriptions-item>
          <el-descriptions-item label="认证等级">{{ detailDialog.cert.certLevel }}</el-descriptions-item>
          <el-descriptions-item label="产品名称">{{ detailDialog.cert.productName }}</el-descriptions-item>
          <el-descriptions-item label="产品型号">{{ detailDialog.cert.productModel }}</el-descriptions-item>
          <el-descriptions-item label="签发日期">{{ detailDialog.cert.issuedAt }}</el-descriptions-item>
          <el-descriptions-item label="过期日期">{{ detailDialog.cert.expiresAt }}</el-descriptions-item>
          <el-descriptions-item label="状态" :span="2">
            <el-tag :type="statusType(detailDialog.cert)">{{ statusLabel(detailDialog.cert) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="detailDialog.cert.revokeReason" label="吊销原因" :span="2">
            {{ detailDialog.cert.revokeReason }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>

    <!-- Revoke Confirm -->
    <el-dialog v-model="revokeDialog.visible" title="吊销证书" width="450px">
      <p>确定要吊销证书 <strong>{{ revokeDialog.certNumber }}</strong> 吗？此操作不可撤销。</p>
      <el-input v-model="revokeDialog.reason" type="textarea" :rows="3" placeholder="请输入吊销原因" />
      <template #footer>
        <el-button @click="revokeDialog.visible = false">取消</el-button>
        <el-button type="danger" @click="doRevoke">确认吊销</el-button>
      </template>
    </el-dialog>

    <!-- Renew Dialog -->
    <el-dialog v-model="renewDialog.visible" title="续期证书" width="450px">
      <p>证书编号：<strong>{{ renewDialog.certNumber }}</strong></p>
      <el-form label-width="100px">
        <el-form-item label="续期年限">
          <el-select v-model="renewDialog.years">
            <el-option :value="1" label="1年" />
            <el-option :value="2" label="2年" />
            <el-option :value="3" label="3年" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renewDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="doRenew">确认续期</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { certApi } from '@/api/cert'
import CertLevelBadge from '@/components/cert/CertLevelBadge.vue'

const loading = ref(false)
const searchQuery = ref('')
const certs = ref<any[]>([])
const page = ref(1)
const total = ref(0)
const pageSize = 20

const detailDialog = reactive({ visible: false, cert: null as any })
const revokeDialog = reactive({ visible: false, certId: 0, certNumber: '', reason: '' })
const renewDialog = reactive({ visible: false, certId: 0, certNumber: '', years: 2 })

function categoryLabel(cat: string): string {
  const map: Record<string, string> = {
    gripper: '末端执行器', sensor: '传感器', wearable: '可穿戴',
    power: '电源', mobility: '移动平台', tool: '工具'
  }
  return map[cat] || cat
}

function statusType(row: any): string {
  if (!row.isActive) return 'danger'
  const exp = new Date(row.expiresAt)
  const now = new Date()
  const days = Math.floor((exp.getTime() - now.getTime()) / 86400000)
  if (days < 30) return 'warning'
  return 'success'
}

function statusLabel(row: any): string {
  if (row.revokedAt) return '已吊销'
  if (!row.isActive) return '已过期'
  return '有效'
}

async function loadCerts() {
  loading.value = true
  try {
    const res = await certApi.listCertificates({ page: page.value - 1, size: pageSize, keyword: searchQuery.value })
    certs.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch {
    ElMessage.error('加载证书列表失败')
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  loadCerts()
}

function handleSort(sort: any) {
  loadCerts()
}

function viewDetail(row: any) {
  detailDialog.cert = row
  detailDialog.visible = true
}

function confirmRevoke(row: any) {
  revokeDialog.certId = row.id
  revokeDialog.certNumber = row.certNumber
  revokeDialog.reason = ''
  revokeDialog.visible = true
}

async function doRevoke() {
  if (!revokeDialog.reason.trim()) {
    ElMessage.warning('请输入吊销原因')
    return
  }
  try {
    await certApi.revokeCertificate(revokeDialog.certId, revokeDialog.reason)
    ElMessage.success('证书已吊销')
    revokeDialog.visible = false
    loadCerts()
  } catch {
    ElMessage.error('吊销失败')
  }
}

function renewCert(row: any) {
  renewDialog.certId = row.id
  renewDialog.certNumber = row.certNumber
  renewDialog.years = 2
  renewDialog.visible = true
}

async function doRenew() {
  try {
    await certApi.renewCertificate(renewDialog.certId, renewDialog.years)
    ElMessage.success(`证书已续期 ${renewDialog.years} 年`)
    renewDialog.visible = false
    loadCerts()
  } catch {
    ElMessage.error('续期失败')
  }
}

onMounted(() => loadCerts())
</script>

<style scoped>
.certificate-manager { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { margin: 0; }
</style>
