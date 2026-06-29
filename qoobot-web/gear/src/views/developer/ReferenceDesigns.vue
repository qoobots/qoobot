<template>
  <div class="reference-designs">
    <div class="header">
      <h2>参考设计库</h2>
      <div class="filters">
        <el-input v-model="searchKeyword" placeholder="搜索设计..." clearable style="width: 240px" @keyup.enter="search" />
        <el-select v-model="filterCategory" placeholder="类别筛选" clearable style="width: 160px; margin-left: 12px" @change="loadDesigns">
          <el-option label="全部" value="" />
          <el-option label="末端执行器" value="end_effector" />
          <el-option label="传感器" value="sensor" />
          <el-option label="可穿戴" value="wearable" />
          <el-option label="电源" value="power" />
          <el-option label="移动平台" value="mobility" />
        </el-select>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="8" v-for="r in filteredDesigns" :key="r.id" style="margin-bottom: 20px">
        <el-card shadow="hover">
          <div class="card-icon">
            <el-icon :size="32"><FolderOpened /></el-icon>
          </div>
          <h4>{{ r.title }}</h4>
          <p class="desc">{{ r.description }}</p>
          <div class="tags">
            <el-tag size="small" :type="categoryTagType(r.category)">{{ categoryLabel(r.category) }}</el-tag>
            <el-tag size="small" type="info" style="margin-left: 6px">{{ r.fileSize }}</el-tag>
          </div>
          <div class="stats">
            <span>📥 {{ r.downloads }} 次下载</span>
            <span>⭐ {{ r.rating }}</span>
          </div>
          <div class="actions">
            <el-button type="primary" size="small" @click="downloadDesign(r)">
              <el-icon><Download /></el-icon> 下载
            </el-button>
            <el-button size="small" @click="previewDesign(r)">预览</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-pagination
      v-model:current-page="page"
      :total="total"
      :page-size="pageSize"
      layout="total, prev, pager, next"
      @current-change="loadDesigns"
      style="margin-top: 20px; justify-content: center"
    />

    <!-- Preview Dialog -->
    <el-dialog v-model="previewDialog.visible" :title="previewDialog.title" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="设计名称">{{ previewDialog.design?.title }}</el-descriptions-item>
        <el-descriptions-item label="类别">{{ categoryLabel(previewDialog.design?.category || '') }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ previewDialog.design?.version || '1.0.0' }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ previewDialog.design?.fileSize || '-' }}</el-descriptions-item>
        <el-descriptions-item label="适用标准">{{ previewDialog.design?.standardRef || '-' }}</el-descriptions-item>
        <el-descriptions-item label="下载次数">{{ previewDialog.design?.downloads || 0 }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ previewDialog.design?.description }}</el-descriptions-item>
        <el-descriptions-item label="包含文件" :span="2">
          <el-tag v-for="f in (previewDialog.design?.files || [])" :key="f" size="small" style="margin-right: 6px">{{ f }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="previewDialog.visible = false">关闭</el-button>
        <el-button type="primary" @click="downloadDesign(previewDialog.design)">下载设计包</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, FolderOpened } from '@element-plus/icons-vue'

const searchKeyword = ref('')
const filterCategory = ref('')
const designs = ref<any[]>([])
const page = ref(1)
const total = ref(0)
const pageSize = 9

const previewDialog = ref({
  visible: false,
  title: '',
  design: null as any
})

const filteredDesigns = computed(() => {
  let result = designs.value
  if (filterCategory.value) {
    result = result.filter(d => d.category === filterCategory.value)
  }
  if (searchKeyword.value) {
    const kw = searchKeyword.value.toLowerCase()
    result = result.filter(d => d.title.toLowerCase().includes(kw) || d.description.toLowerCase().includes(kw))
  }
  return result
})

function categoryLabel(cat: string): string {
  const map: Record<string, string> = {
    end_effector: '末端执行器', sensor: '传感器', wearable: '可穿戴',
    power: '电源', mobility: '移动平台', tool: '工具'
  }
  return map[cat] || cat
}

function categoryTagType(cat: string): string {
  const map: Record<string, string> = { end_effector: '', sensor: 'success', wearable: 'warning', power: 'danger', mobility: 'info' }
  return map[cat] || 'info'
}

async function loadDesigns() {
  try {
    designs.value = [
      { id: 1, title: 'Standard Gripper', description: 'Complete gripper reference design with CAD, PCB, and firmware', category: 'end_effector', fileSize: '45.2 MB', downloads: 1520, rating: 4.8, version: '2.1.0', standardRef: 'MFQ-GRIPPER-V2.0', files: ['gripper_cad.step', 'pcb_gerber.zip', 'firmware_src.zip', 'integration_guide.pdf'] },
      { id: 2, title: 'Smart Sensor Module', description: 'Sensor module with CAN-FD interface and time sync', category: 'sensor', fileSize: '32.8 MB', downloads: 980, rating: 4.6, version: '1.5.0', standardRef: 'MFQ-SENSOR-V1.3', files: ['sensor_pcb.zip', 'firmware.bin', 'datasheet.pdf', 'example_code.zip'] },
      { id: 3, title: 'Wireless Charger', description: 'Qi-compatible wireless charger with alignment guide', category: 'power', fileSize: '28.1 MB', downloads: 650, rating: 4.5, version: '1.2.0', standardRef: 'MFQ-POWER-V1.0', files: ['charger_cad.step', 'coil_design.zip', 'safety_report.pdf'] },
      { id: 4, title: 'Wearable Haptic Band', description: 'Haptic feedback wearable with BLE connectivity', category: 'wearable', fileSize: '18.5 MB', downloads: 420, rating: 4.3, version: '1.0.0', standardRef: 'MFQ-WEARABLE-V1.0', files: ['haptic_band_cad.step', 'ble_profile.json', 'firmware.zip'] },
      { id: 5, title: 'Mecanum Wheel Base', description: 'Omnidirectional mobile platform reference design', category: 'mobility', fileSize: '62.3 MB', downloads: 320, rating: 4.7, version: '1.8.0', standardRef: 'MFQ-MOBILITY-V1.2', files: ['chassis_cad.step', 'motor_driver_pcb.zip', 'kinematics_guide.pdf'] },
      { id: 6, title: 'CAN-FD Protocol Stack', description: 'Reference CAN-FD implementation for accessories', category: 'end_effector', fileSize: '8.2 MB', downloads: 2100, rating: 4.9, version: '2.0.0', standardRef: 'MFQ-COMM-V2.0', files: ['can_fd_stack.c', 'can_fd_stack.h', 'example_main.c', 'integration_guide.pdf'] }
    ]
    total.value = designs.value.length
  } catch {
    ElMessage.error('加载参考设计失败')
  }
}

function search() {
  page.value = 1
  loadDesigns()
}

function downloadDesign(design: any) {
  design.downloads++
  ElMessage.success(`开始下载 "${design.title}"`)
}

function previewDesign(design: any) {
  previewDialog.value.design = design
  previewDialog.value.title = design.title
  previewDialog.value.visible = true
}

onMounted(() => loadDesigns())
</script>

<style scoped>
.reference-designs { padding: 20px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.header h2 { margin: 0; }
.filters { display: flex; }
.card-icon { color: #409eff; margin-bottom: 12px; }
.desc { color: #606266; font-size: 14px; margin: 8px 0; min-height: 40px; }
.tags { margin: 8px 0; }
.stats { display: flex; justify-content: space-between; color: #909399; font-size: 13px; margin: 12px 0; }
.actions { display: flex; gap: 8px; margin-top: 12px; }
</style>
