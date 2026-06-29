<template>
  <div class="cert-list-page">
    <h2>已认证配件目录</h2>
    <p class="desc">浏览所有通过 MFQ 认证的第三方配件</p>

    <el-form :inline="true" class="search-bar">
      <el-form-item>
        <el-input v-model="search" placeholder="搜索配件名称或厂商" clearable>
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </el-form-item>
      <el-form-item>
        <el-select v-model="filterCategory" placeholder="配件类别" clearable>
          <el-option label="末端执行器" value="gripper" />
          <el-option label="传感器模组" value="sensor_module" />
          <el-option label="可穿戴设备" value="wearable" />
          <el-option label="电源配件" value="power" />
          <el-option label="移动平台" value="mobility" />
          <el-option label="工具配件" value="tool" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-select v-model="filterLevel" placeholder="认证等级" clearable>
          <el-option label="MFQ Basic" value="basic" />
          <el-option label="MFQ Premium" value="premium" />
          <el-option label="MFQ Pro" value="pro" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-row :gutter="20">
      <el-col :span="6" v-for="cert in filteredCerts" :key="cert.id">
        <el-card shadow="hover" class="cert-card" @click="$router.push(`/certificates/${cert.id}`)">
          <div class="cert-level">
            <CertLevelBadge :level="cert.certLevel" />
          </div>
          <h4>{{ cert.productName }}</h4>
          <p class="vendor">{{ cert.vendorName }}</p>
          <div class="cert-footer">
            <span class="cert-number">{{ cert.certNumber }}</span>
            <CertStatusTag :status="cert.status" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!filteredCerts.length" description="暂无已认证配件" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import CertLevelBadge from '@/components/cert/CertLevelBadge.vue'
import CertStatusTag from '@/components/cert/CertStatusTag.vue'

const search = ref('')
const filterCategory = ref('')
const filterLevel = ref('')

// 模拟数据
const certificates = ref([
  { id: 1, productName: 'QooGrip Pro', vendorName: 'GripTech', certLevel: 'premium', certNumber: 'MFQ-2026-PREMIUM-0001', status: 'active' },
  { id: 2, productName: 'QooSense Vision', vendorName: 'SensorLab', certLevel: 'basic', certNumber: 'MFQ-2026-BASIC-0002', status: 'active' },
  { id: 3, productName: 'QooPower Pack', vendorName: 'PowerGen', certLevel: 'premium', certNumber: 'MFQ-2026-PREMIUM-0003', status: 'active' },
  { id: 4, productName: 'DexHand Pro', vendorName: 'RoboHands', certLevel: 'pro', certNumber: 'MFQ-2026-PRO-0001', status: 'active' },
  { id: 5, productName: 'QooTouch Array', vendorName: 'TouchSense', certLevel: 'basic', certNumber: 'MFQ-2026-BASIC-0005', status: 'active' },
  { id: 6, productName: 'QooCharge Dock', vendorName: 'ChargeMax', certLevel: 'basic', certNumber: 'MFQ-2026-BASIC-0006', status: 'active' },
  { id: 7, productName: 'QooGlove X', vendorName: 'WearableX', certLevel: 'premium', certNumber: 'MFQ-2026-PREMIUM-0007', status: 'active' },
  { id: 8, productName: 'QooWeld Pro', vendorName: 'WeldTech', certLevel: 'pro', certNumber: 'MFQ-2026-PRO-0002', status: 'active' },
])

const filteredCerts = computed(() => {
  return certificates.value.filter((c) => {
    if (search.value && !c.productName.includes(search.value) && !c.vendorName.includes(search.value)) return false
    if (filterCategory.value) return false  // 模拟：真实场景用 API 过滤
    if (filterLevel.value && c.certLevel !== filterLevel.value) return false
    return true
  })
})
</script>

<style scoped>
.cert-list-page h2 { margin-bottom: 4px; }
.desc { color: #909399; margin-bottom: 20px; }
.search-bar { margin-bottom: 20px; }
.cert-card { cursor: pointer; margin-bottom: 20px; }
.cert-card:hover { border-color: #409eff; }
.cert-card h4 { margin: 12px 0 4px; }
.vendor { color: #909399; font-size: 13px; margin-bottom: 12px; }
.cert-footer { display: flex; justify-content: space-between; align-items: center; }
.cert-number { font-size: 11px; color: #c0c4cc; }
</style>
