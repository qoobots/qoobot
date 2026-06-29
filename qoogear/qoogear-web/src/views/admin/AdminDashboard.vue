<template>
  <div class="admin-dashboard">
    <h2>运营仪表板</h2>
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6" v-for="s in stats" :key="s.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>待审核申请</template>
          <el-table :data="pendingApps" stripe>
            <el-table-column prop="applicationId" label="编号" width="160" />
            <el-table-column prop="companyName" label="公司" />
            <el-table-column prop="productName" label="产品" />
            <el-table-column prop="certLevel" label="等级" width="100" />
            <el-table-column prop="submittedAt" label="提交时间" width="120" />
            <el-table-column label="操作" width="160">
              <template #default>
                <el-button type="primary" link size="small">审核</el-button>
                <el-button type="danger" link size="small">驳回</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>本月统计</template>
          <div class="month-stats">
            <div class="month-item"><span>新申请</span><strong>24</strong></div>
            <div class="month-item"><span>已批准</span><strong>18</strong></div>
            <div class="month-item"><span>已驳回</span><strong>3</strong></div>
            <div class="month-item"><span>待处理</span><strong>3</strong></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
const stats = [
  { value: '128', label: '已认证配件' },
  { value: '320', label: '注册开发者' },
  { value: '15', label: '授权实验室' },
  { value: '36', label: '接口标准' },
]

const pendingApps = [
  { applicationId: 'MFQ-2026-0015', companyName: 'RoboHands', productName: 'DexHand Pro', certLevel: 'pro', submittedAt: '2026-06-28' },
  { applicationId: 'MFQ-2026-0016', companyName: 'TouchSense', productName: 'QooTouch v2', certLevel: 'premium', submittedAt: '2026-06-27' },
  { applicationId: 'MFQ-2026-0017', companyName: 'ChargeMax', productName: 'FastCharge 2', certLevel: 'basic', submittedAt: '2026-06-26' },
]
</script>

<style scoped>
.stats-row { margin-bottom: 20px; }
.stat-card { text-align: center; }
.stat-value { font-size: 32px; font-weight: 700; color: #409eff; }
.stat-label { color: #909399; margin-top: 8px; }
.month-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #ebeef5; }
.month-item strong { font-size: 18px; color: #409eff; }
</style>
