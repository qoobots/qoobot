<template>
  <div class="cla-sign-page">
    <div class="page-header">
      <h1>贡献者许可协议 (CLA)</h1>
      <p>签署贡献者许可协议，成为 QooBot 开源社区的正式贡献者</p>
    </div>

    <div v-if="signed" class="page-card signed-notice">
      <el-result icon="success" title="CLA 已签署" sub-title="您已完成贡献者许可协议的签署">
        <template #extra>
          <el-button type="primary" @click="$router.push('/contributors')">查看贡献者墙</el-button>
        </template>
      </el-result>
    </div>

    <div v-else class="cla-content">
      <div class="page-card">
        <h3>选择协议类型</h3>
        <el-radio-group v-model="claType" class="cla-type-group">
          <el-radio-button value="INDIVIDUAL">个人 CLA</el-radio-button>
          <el-radio-button value="CORPORATE">企业 CLA</el-radio-button>
        </el-radio-group>
      </div>

      <div class="page-card cla-text">
        <h3>贡献者许可协议内容</h3>
        <div class="agreement-text">
          <h4>QooBot 开源社区贡献者许可协议</h4>
          <p>感谢您对 QooBot 项目的关注和贡献。在您提交贡献之前，请仔细阅读并同意以下条款。</p>

          <h5>1. 知识产权许可</h5>
          <p>您特此授予 QooBot 项目及其用户一项永久的、全球性的、非排他的、免版税的、不可撤销的许可，以复制、修改、分发、公开表演、公开展示、创作衍生作品以及以其他方式使用您提交的贡献内容。</p>

          <h5>2. 原创性保证</h5>
          <p>您声明并保证您提交的贡献内容是您的原创作品，您有权授予上述许可。如果您的贡献内容包含第三方材料，您保证已获得必要的授权。</p>

          <h5>3. 行为准则</h5>
          <p>您同意遵守 QooBot 社区的<a href="/governance/charter">行为准则</a>，包括但不限于尊重他人、建设性沟通、接受社区决策。</p>

          <h5>4. 贡献授权</h5>
          <p>您理解并同意，您的贡献可能会被纳入 QooBot 项目的正式版本，并根据项目所采用的开源许可证（Apache 2.0）进行分发。</p>

          <h5>5. 免责声明</h5>
          <p>您的贡献按"原样"提供，不附带任何明示或暗示的担保。QooBot 项目不对因使用您的贡献而产生的任何损害承担责任。</p>
        </div>
      </div>

      <div class="page-card sign-section">
        <el-checkbox v-model="agreed" size="large">我已阅读并同意上述协议内容</el-checkbox>
        <el-button
          type="primary"
          :disabled="!agreed"
          :loading="loading"
          @click="handleSign"
          size="large"
        >
          签署 CLA
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { contributorApi } from '@/api/contributor'
import { ElMessage } from 'element-plus'

const router = useRouter()

const signed = ref(false)
const claType = ref<'INDIVIDUAL' | 'CORPORATE'>('INDIVIDUAL')
const agreed = ref(false)
const loading = ref(false)

onMounted(async () => {
  try {
    const status = await contributorApi.getClaStatus()
    if (status && status.signed) {
      signed.value = true
    }
  } catch {}
})

async function handleSign() {
  if (!agreed.value) return
  loading.value = true
  try {
    await contributorApi.signCla(claType.value)
    ElMessage.success('CLA 签署成功')
    router.push('/contributors')
  } catch {
    ElMessage.error('签署失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.cla-sign-page {
  max-width: 800px;
  margin: 0 auto;
}

.cla-type-group {
  margin-top: 8px;
}

.cla-text {
  h3 {
    margin-bottom: 16px;
  }

  .agreement-text {
    max-height: 400px;
    overflow-y: auto;
    padding: 20px;
    background: var(--qoo-bg);
    border-radius: 8px;
    font-size: 14px;
    line-height: 1.8;
    color: var(--qoo-text);

    h4 {
      font-size: 16px;
      margin-bottom: 16px;
      color: var(--qoo-text);
    }

    h5 {
      font-size: 14px;
      margin: 16px 0 8px;
      color: var(--qoo-primary);
    }

    p {
      margin-bottom: 8px;
      color: var(--qoo-text-secondary);
    }

    a {
      color: var(--qoo-primary);
    }
  }
}

.sign-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.signed-notice {
  text-align: center;
  padding: 48px;
}
</style>
