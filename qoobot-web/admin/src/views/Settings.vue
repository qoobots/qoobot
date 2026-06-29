<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('general')

const generalSettings = reactive({
  siteName: 'QooAuth',
  defaultLanguage: 'en',
  timezone: 'UTC',
  sessionTimeout: 3600,
})

const securitySettings = reactive({
  mfaEnabled: true,
  passwordMinLength: 8,
  passwordRequireSpecial: true,
  maxLoginAttempts: 5,
  lockoutDurationMinutes: 15,
  tokenAccessTtl: 3600,
  tokenRefreshTtl: 2592000,
})

const apiSettings = reactive({
  rateLimitEnabled: true,
  rateLimitCapacity: 100,
  rateLimitRefillRate: 10,
  maxApiKeysPerUser: 20,
  maxDevicesPerUser: 50,
})

function handleSaveGeneral() {
  ElMessage.success('General settings saved')
}

function handleSaveSecurity() {
  ElMessage.success('Security settings saved')
}

function handleSaveApi() {
  ElMessage.success('API settings saved')
}
</script>

<template>
  <div class="settings">
    <h2 class="page-title">Settings</h2>

    <el-tabs v-model="activeTab">
      <!-- General Settings -->
      <el-tab-pane label="General" name="general">
        <el-card shadow="never">
          <el-form :model="generalSettings" label-width="180px">
            <el-form-item label="Site Name">
              <el-input v-model="generalSettings.siteName" />
            </el-form-item>
            <el-form-item label="Default Language">
              <el-select v-model="generalSettings.defaultLanguage">
                <el-option label="English" value="en" />
                <el-option label="Chinese" value="zh" />
                <el-option label="Japanese" value="ja" />
              </el-select>
            </el-form-item>
            <el-form-item label="Timezone">
              <el-select v-model="generalSettings.timezone">
                <el-option label="UTC" value="UTC" />
                <el-option label="Asia/Shanghai" value="Asia/Shanghai" />
                <el-option label="Asia/Tokyo" value="Asia/Tokyo" />
                <el-option label="America/New_York" value="America/New_York" />
              </el-select>
            </el-form-item>
            <el-form-item label="Session Timeout (s)">
              <el-input-number v-model="generalSettings.sessionTimeout" :min="300" :max="86400" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveGeneral">Save</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- Security Settings -->
      <el-tab-pane label="Security" name="security">
        <el-card shadow="never">
          <el-form :model="securitySettings" label-width="220px">
            <el-form-item label="Enable MFA">
              <el-switch v-model="securitySettings.mfaEnabled" />
            </el-form-item>
            <el-form-item label="Min Password Length">
              <el-input-number v-model="securitySettings.passwordMinLength" :min="6" :max="32" />
            </el-form-item>
            <el-form-item label="Require Special Characters">
              <el-switch v-model="securitySettings.passwordRequireSpecial" />
            </el-form-item>
            <el-form-item label="Max Login Attempts">
              <el-input-number v-model="securitySettings.maxLoginAttempts" :min="1" :max="20" />
            </el-form-item>
            <el-form-item label="Lockout Duration (min)">
              <el-input-number v-model="securitySettings.lockoutDurationMinutes" :min="1" :max="1440" />
            </el-form-item>
            <el-form-item label="Access Token TTL (s)">
              <el-input-number v-model="securitySettings.tokenAccessTtl" :min="300" :max="86400" />
            </el-form-item>
            <el-form-item label="Refresh Token TTL (s)">
              <el-input-number v-model="securitySettings.tokenRefreshTtl" :min="3600" :max="31536000" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveSecurity">Save</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- API Settings -->
      <el-tab-pane label="API" name="api">
        <el-card shadow="never">
          <el-form :model="apiSettings" label-width="200px">
            <el-form-item label="Rate Limiting">
              <el-switch v-model="apiSettings.rateLimitEnabled" />
            </el-form-item>
            <el-form-item label="Rate Limit Capacity">
              <el-input-number v-model="apiSettings.rateLimitCapacity" :min="10" :max="10000" />
            </el-form-item>
            <el-form-item label="Rate Limit Refill Rate">
              <el-input-number v-model="apiSettings.rateLimitRefillRate" :min="1" :max="1000" />
            </el-form-item>
            <el-form-item label="Max API Keys / User">
              <el-input-number v-model="apiSettings.maxApiKeysPerUser" :min="1" :max="100" />
            </el-form-item>
            <el-form-item label="Max Devices / User">
              <el-input-number v-model="apiSettings.maxDevicesPerUser" :min="1" :max="500" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveApi">Save</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.settings {
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: #1a1a1a;
    margin-bottom: 24px;
  }
}
</style>
