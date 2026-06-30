<template>
  <div class="brand-assets-page">
    <div class="page-header">
      <h1>品牌资产</h1>
      <p>QooBot Logo、字体、配色规范、社区周边设计、品牌指南——统一品牌形象</p>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="Logo" name="logo">
        <div class="page-card">
          <h2>🧬 QooBot Logo</h2>
          <p style="color: var(--qoo-text-secondary); margin-bottom: 20px">
            所有 Logo 文件以 SVG 和 PNG 格式提供。使用时请遵循下方品牌指南。
          </p>
          <el-row :gutter="20">
            <el-col :span="8" v-for="logo in logos" :key="logo.name">
              <el-card shadow="hover" class="logo-card">
                <div class="logo-preview" :style="{ background: logo.bg }">
                  <div class="logo-placeholder">{{ logo.label }}</div>
                </div>
                <div class="logo-actions">
                  <span style="font-weight: 500">{{ logo.name }}</span>
                  <div>
                    <el-button size="small" link>SVG</el-button>
                    <el-button size="small" link>PNG</el-button>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>
      <el-tab-pane label="配色" name="colors">
        <div class="page-card">
          <h2>🎨 品牌色板</h2>
          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="6" v-for="color in colors" :key="color.name">
              <div class="color-swatch" :style="{ background: color.hex }">
                <div class="color-label">{{ color.name }}</div>
                <div class="color-hex">{{ color.hex }}</div>
              </div>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>
      <el-tab-pane label="字体" name="typography">
        <div class="page-card">
          <h2>✍️ 字体规范</h2>
          <el-table :data="fonts" stripe style="margin-top: 12px">
            <el-table-column prop="usage" label="用途" width="180" />
            <el-table-column prop="family" label="字体族" width="280" />
            <el-table-column prop="weight" label="字重" width="120" />
            <el-table-column prop="example" label="示例">
              <template #default="{ row }">
                <span :style="{ fontFamily: row.family, fontWeight: row.weight, fontSize: row.size }">
                  QooBot 仿生人
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
      <el-tab-pane label="周边" name="merchandise">
        <div class="page-card">
          <h2>🎁 社区周边</h2>
          <el-row :gutter="20">
            <el-col :span="6" v-for="item in merchandise" :key="item.name">
              <el-card shadow="hover" class="merch-card">
                <div class="merch-icon">{{ item.icon }}</div>
                <h3>{{ item.name }}</h3>
                <p style="font-size: 13px; color: var(--qoo-text-secondary)">{{ item.desc }}</p>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>
    </el-tabs>

    <div class="page-card" style="margin-top: 20px">
      <h2>📋 品牌使用指南</h2>
      <el-collapse>
        <el-collapse-item title="Logo 使用规范" name="1">
          <ul style="line-height: 2; padding-left: 20px; color: var(--qoo-text-secondary)">
            <li>保持 Logo 的纵横比，不得拉伸或压缩</li>
            <li>Logo 周围保留足够的留白空间（至少等于 Logo 高度的 1/4）</li>
            <li>不得修改 Logo 的颜色、添加阴影或特效</li>
            <li>在深色背景上使用白色版本，浅色背景上使用标准版本</li>
          </ul>
        </el-collapse-item>
        <el-collapse-item title="名称使用" name="2">
          <ul style="line-height: 2; padding-left: 20px; color: var(--qoo-text-secondary)">
            <li>正确写法：<strong>QooBot</strong>（Q 和 B 大写）</li>
            <li>禁止使用：qoobot、Qoo Bot、QOOBOT</li>
            <li>技术文档中可使用小写 <code>qoobot</code> 指代代码库或命令行工具</li>
          </ul>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('logo')

const logos = [
  { name: '标准 Logo', label: 'QooBot', bg: '#4A90D9', type: 'color' },
  { name: '白色 Logo', label: 'QooBot', bg: '#1a1a2e', type: 'white' },
  { name: 'Icon 图标', label: 'Q', bg: '#4A90D9', type: 'icon' },
]

const colors = [
  { name: 'Primary', hex: '#4A90D9' },
  { name: 'Secondary', hex: '#34C759' },
  { name: 'Accent', hex: '#FF6B35' },
  { name: 'Dark', hex: '#1A1A2E' },
  { name: 'Light BG', hex: '#F8F9FA' },
  { name: 'Text Secondary', hex: '#6C757D' },
  { name: 'Border', hex: '#E5E7EB' },
  { name: 'Success', hex: '#67C23A' },
]

const fonts = [
  { usage: '标题 Heading', family: '-apple-system, BlinkMacSystemFont, sans-serif', weight: '700', size: '24px' },
  { usage: '正文 Body', family: '-apple-system, BlinkMacSystemFont, "Noto Sans SC", sans-serif', weight: '400', size: '15px' },
  { usage: '代码 Code', family: '"JetBrains Mono", "Fira Code", monospace', weight: '400', size: '14px' },
]

const merchandise = [
  { icon: '👕', name: 'T 恤', desc: 'QooBot 开发者限定款' },
  { icon: '🧢', name: '棒球帽', desc: '刺绣 Logo 棒球帽' },
  { icon: '📱', name: '贴纸包', desc: 'QooBot 系列贴纸' },
  { icon: '☕', name: '马克杯', desc: '陶瓷马克杯' },
]
</script>

<style lang="scss" scoped>
.logo-card { :deep(.el-card__body) { padding: 0; } }
.logo-preview {
  height: 140px; display: flex; align-items: center; justify-content: center;
  .logo-placeholder { font-size: 28px; font-weight: 700; color: white; }
}
.logo-actions { padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; }
.color-swatch {
  height: 120px; border-radius: 8px; position: relative; overflow: hidden; margin-bottom: 12px;
  .color-label { position: absolute; top: 12px; left: 12px; color: white; font-weight: 600; }
  .color-hex { position: absolute; bottom: 12px; left: 12px; color: rgba(255,255,255,.7); font-family: monospace; font-size: 14px; }
}
.merch-card { text-align: center;
  .merch-icon { font-size: 40px; margin-bottom: 8px; }
  h3 { font-size: 16px; margin-bottom: 4px; }
}
h2 { font-size: 20px; }
</style>
