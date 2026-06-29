<template>
  <div class="standard-list-page">
    <h2>MFQ 接口标准</h2>
    <p class="desc">QooBot 配件兼容性接口规范文档</p>

    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane v-for="cat in categories" :key="cat.slug" :label="cat.name" :name="cat.slug">
        <el-table :data="getSpecsByCategory(cat.slug)" stripe>
          <el-table-column prop="specNumber" label="规范编号" width="140" />
          <el-table-column prop="title" label="标题" />
          <el-table-column prop="version" label="版本" width="100" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="publishedAt" label="发布日期" width="120" />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button type="primary" link @click="$router.push(`/standards/${row.id}`)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('mechanical')

const categories = [
  { name: '机械接口', slug: 'mechanical' },
  { name: '电气接口', slug: 'electrical' },
  { name: '通信协议', slug: 'communication' },
  { name: '安全规范', slug: 'safety' },
  { name: '末端执行器', slug: 'end_effector' },
  { name: '传感器模组', slug: 'sensor' },
  { name: '电源配件', slug: 'power' },
]

const specs = [
  { id: 1, specNumber: 'MFQ-SPEC-0001', title: 'Mechanical Flange Interface Standard', version: '1.2.0', status: 'published', publishedAt: '2026-01-15', category: 'mechanical' },
  { id: 2, specNumber: 'MFQ-SPEC-0002', title: 'Electrical Power Interface Standard', version: '1.1.0', status: 'published', publishedAt: '2026-02-01', category: 'electrical' },
  { id: 3, specNumber: 'MFQ-SPEC-0003', title: 'CAN-FD Communication Protocol', version: '2.0.0', status: 'published', publishedAt: '2026-03-10', category: 'communication' },
  { id: 4, specNumber: 'MFQ-SPEC-0004', title: 'Safety Requirements for Accessories', version: '1.0.0', status: 'published', publishedAt: '2026-01-20', category: 'safety' },
  { id: 10, specNumber: 'MFQ-SPEC-0010', title: 'End Effector Standard', version: '1.3.0', status: 'published', publishedAt: '2026-04-01', category: 'end_effector' },
  { id: 20, specNumber: 'MFQ-SPEC-0020', title: 'Sensor Module Standard', version: '1.0.0', status: 'published', publishedAt: '2026-05-15', category: 'sensor' },
  { id: 30, specNumber: 'MFQ-SPEC-0030', title: 'Power Accessory Standard', version: '1.1.0', status: 'published', publishedAt: '2026-06-01', category: 'power' },
]

function getSpecsByCategory(cat: string) {
  return specs.filter((s) => s.category === cat)
}
</script>

<style scoped>
.desc { color: #909399; margin-bottom: 20px; }
</style>
