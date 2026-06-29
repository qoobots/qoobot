<template>
  <div class="home-page">
    <section class="hero">
      <h1>Made for QooBot</h1>
      <p class="subtitle">MFQ 认证体系 — 让第三方配件无缝融入 QooBot 生态</p>
      <div class="hero-actions">
        <el-button type="primary" size="large" @click="$router.push('/certificates')">浏览认证配件</el-button>
        <el-button size="large" @click="$router.push('/dev')">成为开发者</el-button>
      </div>
    </section>

    <section class="stats">
      <el-row :gutter="24">
        <el-col :span="6" v-for="s in statsData" :key="s.label">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </el-card>
        </el-col>
      </el-row>
    </section>

    <section class="levels">
      <h2>三级认证体系</h2>
      <el-row :gutter="24">
        <el-col :span="8" v-for="l in levels" :key="l.name">
          <el-card class="level-card">
            <div class="level-header">
              <el-tag :type="l.color" size="large">{{ l.name }}</el-tag>
            </div>
            <p class="level-desc">{{ l.desc }}</p>
            <ul class="level-features">
              <li v-for="f in l.features" :key="f">{{ f }}</li>
            </ul>
          </el-card>
        </el-col>
      </el-row>
    </section>

    <section class="categories">
      <h2>配件类别</h2>
      <el-row :gutter="16">
        <el-col :span="4" v-for="c in categories" :key="c.name">
          <el-card shadow="hover" class="category-card" @click="$router.push('/standards')">
            <el-icon :size="32"><component :is="c.icon" /></el-icon>
            <div class="cat-name">{{ c.name }}</div>
            <div class="cat-count">{{ c.count }} 项标准</div>
          </el-card>
        </el-col>
      </el-row>
    </section>
  </div>
</template>

<script setup lang="ts">
const statsData = [
  { value: '128+', label: '已认证配件' },
  { value: '36', label: '接口标准' },
  { value: '15', label: '授权实验室' },
  { value: '3,200+', label: '注册开发者' },
]

const levels = [
  { name: 'MFQ Basic', color: '', desc: '基础兼容认证', features: ['物理接口兼容', '电气规范合规', '通信协议握手', '有效期 1 年'] },
  { name: 'MFQ Premium', color: 'warning', desc: '深度集成认证', features: ['全部 Basic 要求', '功能互操作测试', '安全认证审查', '有效期 2 年'] },
  { name: 'MFQ Pro', color: 'danger', desc: '专业级认证', features: ['全部 Premium 要求', '冗余安全审计', 'FMEA 分析', '有效期 3 年'] },
]

const categories = [
  { name: '末端执行器', icon: 'SetUp', count: 8 },
  { name: '传感器模组', icon: 'Camera', count: 7 },
  { name: '可穿戴设备', icon: 'Watch', count: 5 },
  { name: '电源配件', icon: 'Lightning', count: 4 },
  { name: '移动平台', icon: 'Van', count: 6 },
  { name: '工具配件', icon: 'Tools', count: 6 },
]
</script>

<style scoped>
.hero { text-align: center; padding: 60px 0 40px; }
.hero h1 { font-size: 42px; color: #303133; margin-bottom: 12px; }
.subtitle { font-size: 18px; color: #909399; margin-bottom: 32px; }
.hero-actions { display: flex; gap: 16px; justify-content: center; }
.stats { padding: 40px 0; }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; color: #409eff; }
.stat-label { font-size: 14px; color: #909399; margin-top: 8px; }
.levels, .categories { padding: 40px 0; }
.levels h2, .categories h2 { text-align: center; margin-bottom: 24px; }
.level-card { text-align: center; }
.level-header { margin-bottom: 16px; }
.level-desc { color: #606266; margin-bottom: 12px; }
.level-features { text-align: left; padding-left: 20px; color: #909399; font-size: 13px; }
.level-features li { margin-bottom: 6px; }
.category-card { text-align: center; cursor: pointer; }
.category-card:hover { border-color: #409eff; }
.cat-name { margin-top: 12px; font-weight: 600; }
.cat-count { font-size: 12px; color: #909399; margin-top: 4px; }
</style>
