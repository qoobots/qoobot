<template>
  <div class="laboratory-manager">
    <div class="header">
      <h2>实验室管理</h2>
      <el-button type="primary" @click="showRegisterDialog">
        <el-icon><Plus /></el-icon> 注册实验室
      </el-button>
    </div>

    <el-table :data="labs" stripe v-loading="loading">
      <el-table-column prop="name" label="实验室名称" />
      <el-table-column prop="address" label="地址" />
      <el-table-column prop="contactName" label="联系人" width="100" />
      <el-table-column prop="accredited" label="认证状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.accredited ? 'success' : 'warning'">
            {{ row.accredited ? '已认证' : '待认证' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="scope" label="测试范围">
        <template #default="{ row }">
          <el-tag v-for="s in (row.scope || [])" :key="s" size="small" style="margin-right: 4px">{{ s }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="equipmentCount" label="设备数" width="80" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" link @click="viewDetail(row)">详情</el-button>
          <el-button v-if="!row.accredited" type="success" size="small" link @click="accreditLab(row)">认证</el-button>
          <el-button type="danger" size="small" link @click="suspendLab(row)">暂停</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Register Dialog -->
    <el-dialog v-model="registerDialog.visible" title="注册实验室" width="600px">
      <el-form :model="registerDialog.form" label-width="100px">
        <el-form-item label="实验室名称" required>
          <el-input v-model="registerDialog.form.name" />
        </el-form-item>
        <el-form-item label="地址" required>
          <el-input v-model="registerDialog.form.address" />
        </el-form-item>
        <el-form-item label="国家/地区" required>
          <el-select v-model="registerDialog.form.country" style="width: 100%">
            <el-option label="中国" value="CN" />
            <el-option label="美国" value="US" />
            <el-option label="德国" value="DE" />
            <el-option label="日本" value="JP" />
            <el-option label="韩国" value="KR" />
          </el-select>
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="registerDialog.form.contactName" />
        </el-form-item>
        <el-form-item label="联系邮箱">
          <el-input v-model="registerDialog.form.contactEmail" />
        </el-form-item>
        <el-form-item label="测试范围" required>
          <el-select v-model="registerDialog.form.scope" style="width: 100%" multiple>
            <el-option label="机械" value="机械" />
            <el-option label="电气" value="电气" />
            <el-option label="安全" value="安全" />
            <el-option label="通信" value="通信" />
            <el-option label="传感器" value="传感器" />
            <el-option label="电磁兼容" value="电磁兼容" />
            <el-option label="环境" value="环境" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="registerLab">注册</el-button>
      </template>
    </el-dialog>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailDialog.visible" title="实验室详情" width="600px">
      <template v-if="detailDialog.lab">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="名称">{{ detailDialog.lab.name }}</el-descriptions-item>
          <el-descriptions-item label="认证状态">
            <el-tag :type="detailDialog.lab.accredited ? 'success' : 'warning'">
              {{ detailDialog.lab.accredited ? '已认证' : '待认证' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="地址" :span="2">{{ detailDialog.lab.address }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ detailDialog.lab.contactName || '-' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ detailDialog.lab.contactEmail || '-' }}</el-descriptions-item>
          <el-descriptions-item label="测试范围" :span="2">
            <el-tag v-for="s in (detailDialog.lab.scope || [])" :key="s" size="small" style="margin-right: 4px">{{ s }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const loading = ref(false)
const labs = ref<any[]>([])

const registerDialog = reactive({
  visible: false,
  form: { name: '', address: '', country: '', contactName: '', contactEmail: '', scope: [] as string[] }
})

const detailDialog = reactive({
  visible: false,
  lab: null as any
})

async function loadLabs() {
  loading.value = true
  try {
    labs.value = [
      { id: 1, name: '华南机器人测试中心', address: '深圳市南山区科技园', contactName: '王工', contactEmail: 'wang@lab.cn', accredited: true, scope: ['机械', '电气', '安全'], equipmentCount: 45 },
      { id: 2, name: '华东传感器实验室', address: '上海市浦东新区张江', contactName: '李工', contactEmail: 'li@lab.cn', accredited: true, scope: ['传感器', '通信'], equipmentCount: 32 },
      { id: 3, name: '华北EMC测试中心', address: '北京市海淀区', contactName: '张工', contactEmail: 'zhang@lab.cn', accredited: false, scope: ['电磁兼容', '环境'], equipmentCount: 28 }
    ]
  } finally {
    loading.value = false
  }
}

function showRegisterDialog() {
  registerDialog.form = { name: '', address: '', country: '', contactName: '', contactEmail: '', scope: [] }
  registerDialog.visible = true
}

async function registerLab() {
  try {
    labs.value.push({
      id: Date.now(),
      name: registerDialog.form.name,
      address: registerDialog.form.address,
      contactName: registerDialog.form.contactName,
      contactEmail: registerDialog.form.contactEmail,
      accredited: false,
      scope: registerDialog.form.scope,
      equipmentCount: 0
    })
    registerDialog.visible = false
    ElMessage.success('实验室已注册')
  } catch {
    ElMessage.error('注册失败')
  }
}

function viewDetail(row: any) {
  detailDialog.lab = row
  detailDialog.visible = true
}

async function accreditLab(row: any) {
  try {
    await ElMessageBox.confirm(`确认认证实验室 "${row.name}"？`, '认证确认', { type: 'warning' })
    row.accredited = true
    ElMessage.success('实验室已认证')
  } catch { /* cancelled */ }
}

async function suspendLab(row: any) {
  try {
    await ElMessageBox.confirm(`确定暂停实验室 "${row.name}"？暂停后将不再分配新任务。`, '暂停确认', { type: 'warning' })
    row.accredited = false
    ElMessage.success('实验室已暂停')
  } catch { /* cancelled */ }
}

onMounted(() => loadLabs())
</script>

<style scoped>
.laboratory-manager { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { margin: 0; }
</style>
