<template>
  <div class="test-kits">
    <h2>测试治具</h2>
    <p class="subtitle">官方认证测试治具，确保配件符合 MFQ 规范</p>

    <el-row :gutter="20">
      <el-col :span="8" v-for="k in kits" :key="k.id" style="margin-bottom: 20px">
        <el-card shadow="hover">
          <div class="kit-icon">
            <el-icon :size="36"><Tools /></el-icon>
          </div>
          <h4>{{ k.name }}</h4>
          <p class="desc">{{ k.description }}</p>
          <div class="specs">
            <div class="spec-item">
              <span class="label">价格</span>
              <span class="value price">¥{{ k.price.toLocaleString() }}</span>
            </div>
            <div class="spec-item">
              <span class="label">库存</span>
              <span class="value" :class="{ 'low-stock': k.stock < 10 }">{{ k.stock }} 件</span>
            </div>
            <div class="spec-item">
              <span class="label">类别</span>
              <el-tag size="small">{{ k.category }}</el-tag>
            </div>
          </div>
          <div style="margin-top: 16px">
            <el-button type="primary" @click="orderKit(k)" :disabled="k.stock <= 0">
              <el-icon><ShoppingCart /></el-icon> 订购
            </el-button>
            <el-button @click="viewDetail(k)">详情</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailDialog.visible" :title="detailDialog.kit?.name" width="600px">
      <template v-if="detailDialog.kit">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="名称">{{ detailDialog.kit.name }}</el-descriptions-item>
          <el-descriptions-item label="价格">¥{{ detailDialog.kit.price?.toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="类别">{{ detailDialog.kit.category }}</el-descriptions-item>
          <el-descriptions-item label="库存">{{ detailDialog.kit.stock }} 件</el-descriptions-item>
          <el-descriptions-item label="适用标准">{{ detailDialog.kit.standardRef || '-' }}</el-descriptions-item>
          <el-descriptions-item label="交付周期">{{ detailDialog.kit.leadTime || '2-4周' }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ detailDialog.kit.description }}</el-descriptions-item>
        </el-descriptions>
      </template>
      <template #footer>
        <el-button @click="detailDialog.visible = false">关闭</el-button>
        <el-button type="primary" @click="orderKit(detailDialog.kit)">订购</el-button>
      </template>
    </el-dialog>

    <!-- Order Dialog -->
    <el-dialog v-model="orderDialog.visible" title="订购测试治具" width="500px">
      <p>治具：<strong>{{ orderDialog.kitName }}</strong></p>
      <el-form label-width="80px">
        <el-form-item label="数量">
          <el-input-number v-model="orderDialog.quantity" :min="1" :max="orderDialog.maxStock" />
        </el-form-item>
        <el-form-item label="收货地址">
          <el-input v-model="orderDialog.address" type="textarea" :rows="2" placeholder="请输入收货地址" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="orderDialog.note" placeholder="其他要求（可选）" />
        </el-form-item>
      </el-form>
      <div class="order-total">
        总计：<strong>¥{{ (orderDialog.quantity * orderDialog.unitPrice).toLocaleString() }}</strong>
      </div>
      <template #footer>
        <el-button @click="orderDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmOrder">确认订购</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Tools, ShoppingCart } from '@element-plus/icons-vue'

const kits = ref([
  { id: 1, name: 'Mechanical Fit Gauge', description: 'Flange alignment and fit testing tool for QooBot mechanical interface', category: '机械', price: 299, stock: 50, standardRef: 'MFQ-MECH-V2.0', leadTime: '1-2周' },
  { id: 2, name: 'Electrical Test Harness', description: 'Voltage/current/pinout validation harness with automated testing', category: '电气', price: 499, stock: 30, standardRef: 'MFQ-ELEC-V1.3', leadTime: '2-3周' },
  { id: 3, name: 'Protocol Analyzer', description: 'CAN-FD/RS-485 protocol capture and analysis with MFQ compliance checks', category: '通信', price: 999, stock: 20, standardRef: 'MFQ-COMM-V2.0', leadTime: '3-4周' },
  { id: 4, name: 'EMC Pre-Compliance Kit', description: 'Pre-compliance EMC testing kit for radiated/conducted emissions', category: 'EMC', price: 1499, stock: 8, standardRef: 'MFQ-EMC-V1.0', leadTime: '4-6周' },
  { id: 5, name: 'Safety Test Station', description: 'All-in-one safety testing station: e-stop, overcurrent, overtemperature', category: '安全', price: 2499, stock: 5, standardRef: 'MFQ-SAFETY-V1.0', leadTime: '4-8周' },
  { id: 6, name: 'Environmental Chamber Adapter', description: 'Adapter kit for environmental testing with temperature/humidity chambers', category: '环境', price: 799, stock: 12, standardRef: 'MFQ-ENV-V1.0', leadTime: '2-3周' }
])

const detailDialog = reactive({ visible: false, kit: null as any })
const orderDialog = reactive({ visible: false, kitId: 0, kitName: '', unitPrice: 0, maxStock: 0, quantity: 1, address: '', note: '' })

function viewDetail(kit: any) {
  detailDialog.kit = kit
  detailDialog.visible = true
}

function orderKit(kit: any) {
  if (kit.stock <= 0) {
    ElMessage.warning('库存不足')
    return
  }
  orderDialog.kitId = kit.id
  orderDialog.kitName = kit.name
  orderDialog.unitPrice = kit.price
  orderDialog.maxStock = kit.stock
  orderDialog.quantity = 1
  orderDialog.address = ''
  orderDialog.note = ''
  orderDialog.visible = true
}

function confirmOrder() {
  const kit = kits.value.find(k => k.id === orderDialog.kitId)
  if (kit) {
    kit.stock -= orderDialog.quantity
  }
  orderDialog.visible = false
  ElMessage.success(`已订购 ${orderDialog.quantity} 件 "${orderDialog.kitName}"`)
}
</script>

<style scoped>
.test-kits { padding: 20px; }
.subtitle { color: #909399; margin-bottom: 24px; }
.kit-icon { color: #e6a23c; margin-bottom: 12px; }
.desc { color: #606266; font-size: 14px; margin: 8px 0; min-height: 40px; }
.specs { display: flex; flex-direction: column; gap: 6px; margin: 12px 0; }
.spec-item { display: flex; justify-content: space-between; align-items: center; }
.spec-item .label { color: #909399; font-size: 13px; }
.spec-item .value { font-weight: 500; }
.price { color: #f56c6c; }
.low-stock { color: #e6a23c; }
.order-total { text-align: right; margin-top: 16px; font-size: 16px; }
</style>
