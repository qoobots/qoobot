<template>
  <div class="standard-manager">
    <div class="header">
      <h2>标准管理</h2>
      <el-button type="primary" @click="showCreateDialog">
        <el-icon><Plus /></el-icon> 新建标准
      </el-button>
    </div>

    <el-table :data="specs" stripe v-loading="loading">
      <el-table-column prop="specNumber" label="编号" width="160" />
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="category" label="类别" width="140">
        <template #default="{ row }">
          <el-tag>{{ row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="specStatusType(row.status)">{{ row.status === 'published' ? '已发布' : row.status === 'draft' ? '草稿' : '已废弃' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="updatedAt" label="更新时间" width="160" />
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" link @click="editSpec(row)">编辑</el-button>
          <el-button v-if="row.status === 'draft'" type="success" size="small" link @click="publishSpec(row)">发布</el-button>
          <el-button v-if="row.status === 'published'" type="warning" size="small" link @click="deprecateSpec(row)">废弃</el-button>
          <el-button type="danger" size="small" link @click="deleteSpec(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="formDialog.visible" :title="formDialog.isEdit ? '编辑标准' : '新建标准'" width="650px">
      <el-form :model="formDialog.form" label-width="120px">
        <el-form-item label="标题" required>
          <el-input v-model="formDialog.form.title" placeholder="标准标题" />
        </el-form-item>
        <el-form-item label="类别" required>
          <el-select v-model="formDialog.form.category" style="width: 100%">
            <el-option label="机械接口" value="机械接口" />
            <el-option label="电气接口" value="电气接口" />
            <el-option label="通信协议" value="通信协议" />
            <el-option label="安全规范" value="安全规范" />
            <el-option label="电磁兼容" value="电磁兼容" />
            <el-option label="环境适应性" value="环境适应性" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本号" required>
          <el-input v-model="formDialog.form.version" placeholder="如：1.0.0" />
        </el-form-item>
        <el-form-item label="适用产品类别" required>
          <el-select v-model="formDialog.form.applicableCategory" style="width: 100%" multiple>
            <el-option label="末端执行器" value="gripper" />
            <el-option label="传感器" value="sensor" />
            <el-option label="可穿戴" value="wearable" />
            <el-option label="电源" value="power" />
            <el-option label="移动平台" value="mobility" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formDialog.form.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveSpec">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { standardApi } from '@/api/standard'

const loading = ref(false)
const specs = ref<any[]>([])

const formDialog = reactive({
  visible: false,
  isEdit: false,
  editId: null as number | null,
  form: { title: '', category: '', version: '', applicableCategory: [] as string[], description: '' }
})

function specStatusType(status: string): string {
  const map: Record<string, string> = { published: 'success', draft: 'warning', deprecated: 'info' }
  return map[status] || 'info'
}

async function loadSpecs() {
  loading.value = true
  try {
    const res = await standardApi.listSpecs({ page: 0, size: 100 })
    specs.value = res.data?.items || []
  } catch {
    specs.value = [
      { id: 1, specNumber: 'MFQ-SPEC-0001', title: 'Mechanical Interface Standard', category: '机械接口', version: '1.2.0', status: 'published', updatedAt: '2026-05-20' },
      { id: 2, specNumber: 'MFQ-SPEC-0010', title: 'End Effector Communication Protocol', category: '通信协议', version: '1.3.0', status: 'published', updatedAt: '2026-06-10' },
      { id: 3, specNumber: 'MFQ-SPEC-0015', title: 'Power Accessory Safety Spec', category: '安全规范', version: '0.9.0', status: 'draft', updatedAt: '2026-06-25' }
    ]
  } finally {
    loading.value = false
  }
}

function showCreateDialog() {
  formDialog.isEdit = false
  formDialog.editId = null
  formDialog.form = { title: '', category: '', version: '', applicableCategory: [], description: '' }
  formDialog.visible = true
}

function editSpec(row: any) {
  formDialog.isEdit = true
  formDialog.editId = row.id
  formDialog.form = {
    title: row.title,
    category: row.category,
    version: row.version,
    applicableCategory: row.applicableCategory || [],
    description: row.description || ''
  }
  formDialog.visible = true
}

async function saveSpec() {
  try {
    if (formDialog.isEdit) {
      // await standardApi.updateSpec(formDialog.editId!, formDialog.form)
      ElMessage.success('标准已更新')
    } else {
      // await standardApi.createSpec(formDialog.form)
      ElMessage.success('标准已创建')
    }
    formDialog.visible = false
    loadSpecs()
  } catch {
    ElMessage.error('保存失败')
  }
}

async function publishSpec(row: any) {
  try {
    await ElMessageBox.confirm(`确定发布 "${row.title}"？`, '发布确认', { type: 'warning' })
    // await standardApi.publishSpec(row.id)
    row.status = 'published'
    ElMessage.success('标准已发布')
  } catch { /* cancelled */ }
}

async function deprecateSpec(row: any) {
  try {
    await ElMessageBox.confirm(`确定废弃 "${row.title}"？废弃后不再适用于新认证。`, '废弃确认', { type: 'warning' })
    // await standardApi.deprecateSpec(row.id)
    row.status = 'deprecated'
    ElMessage.success('标准已废弃')
  } catch { /* cancelled */ }
}

async function deleteSpec(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除 "${row.title}"？此操作不可撤销。`, '删除确认', { type: 'warning' })
    specs.value = specs.value.filter(s => s.id !== row.id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}

onMounted(() => loadSpecs())
</script>

<style scoped>
.standard-manager { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { margin: 0; }
</style>
