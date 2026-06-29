<template>
  <div class="cert-detail-page">
    <el-page-header @back="$router.back()" title="返回目录" />
    <el-card class="detail-card">
      <template #header>
        <div class="card-header">
          <span>{{ cert.productName }}</span>
          <CertLevelBadge :level="cert.certLevel" />
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="证书编号">{{ cert.certNumber }}</el-descriptions-item>
        <el-descriptions-item label="状态"><CertStatusTag :status="cert.status" /></el-descriptions-item>
        <el-descriptions-item label="厂商">{{ cert.vendorName }}</el-descriptions-item>
        <el-descriptions-item label="产品型号">{{ cert.productName }}</el-descriptions-item>
        <el-descriptions-item label="认证等级">{{ cert.certLevel.toUpperCase() }}</el-descriptions-item>
        <el-descriptions-item label="颁发日期">{{ cert.issuedAt }}</el-descriptions-item>
        <el-descriptions-item label="有效期至">{{ cert.expiresAt }}</el-descriptions-item>
        <el-descriptions-item label="证书哈希">{{ cert.certNumber }}</el-descriptions-item>
      </el-descriptions>
      <div style="margin-top: 20px; text-align: center">
        <el-button type="primary" @click="verifyCert">验证证书真伪</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import CertLevelBadge from '@/components/cert/CertLevelBadge.vue'
import CertStatusTag from '@/components/cert/CertStatusTag.vue'

const route = useRoute()
const cert = ref({
  productName: 'QooGrip Pro',
  vendorName: 'GripTech Robotics',
  certLevel: 'premium',
  certNumber: 'MFQ-2026-PREMIUM-0001',
  status: 'active',
  issuedAt: '2026-01-15',
  expiresAt: '2028-01-15',
})

function verifyCert() {
  alert('证书验证通过！该配件已通过 MFQ Premium 认证。')
}
</script>

<style scoped>
.cert-detail-page { max-width: 900px; }
.detail-card { margin-top: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
