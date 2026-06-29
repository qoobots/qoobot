<template>
  <div class="application-create">
    <h2>新建 MFQ 认证申请</h2>
    <el-card>
      <el-form :model="form" label-width="140px" style="max-width: 800px">
        <el-divider>开发者信息</el-divider>
        <el-form-item label="公司名称" required>
          <el-input v-model="form.companyName" placeholder="输入公司名称" />
        </el-form-item>
        <el-form-item label="联系人" required>
          <el-input v-model="form.contactName" placeholder="输入联系人姓名" />
        </el-form-item>
        <el-form-item label="联系邮箱" required>
          <el-input v-model="form.contactEmail" placeholder="cert@company.com" />
        </el-form-item>
        <el-form-item label="公司网站">
          <el-input v-model="form.website" placeholder="https://company.com" />
        </el-form-item>

        <el-divider>产品信息</el-divider>
        <el-form-item label="产品名称" required>
          <el-input v-model="form.productName" placeholder="输入产品名称" />
        </el-form-item>
        <el-form-item label="产品型号" required>
          <el-input v-model="form.productModel" placeholder="输入型号" />
        </el-form-item>
        <el-form-item label="产品类别" required>
          <el-select v-model="form.productCategory" placeholder="选择类别">
            <el-option label="末端执行器" value="gripper" />
            <el-option label="传感器模组" value="sensor_module" />
            <el-option label="可穿戴设备" value="wearable" />
            <el-option label="电源配件" value="power" />
            <el-option label="移动平台配件" value="mobility" />
            <el-option label="工具配件" value="tool" />
          </el-select>
        </el-form-item>
        <el-form-item label="认证等级" required>
          <el-radio-group v-model="form.certLevel">
            <el-radio value="basic">MFQ Basic — 基础兼容</el-radio>
            <el-radio value="premium">MFQ Premium — 深度集成</el-radio>
            <el-radio value="pro">MFQ Pro — 专业级</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="产品描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="描述产品功能和用途" />
        </el-form-item>
        <el-form-item label="技术文档">
          <el-upload drag>
            <el-icon><UploadFilled /></el-icon>
            <div>拖拽文件到此处或点击上传</div>
            <template #tip>支持机械图纸、电气原理图、通信协议文档</template>
          </el-upload>
        </el-form-item>

        <el-divider />
        <el-form-item>
          <el-button type="primary" size="large" @click="submit">保存为草稿</el-button>
          <el-button size="large" @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

const form = reactive({
  companyName: '',
  contactName: '',
  contactEmail: '',
  website: '',
  productName: '',
  productModel: '',
  productCategory: '',
  certLevel: 'basic',
  description: '',
})

function submit() {
  ElMessage.success('申请已保存为草稿')
}
</script>
