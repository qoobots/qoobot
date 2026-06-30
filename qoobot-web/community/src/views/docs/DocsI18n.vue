<template>
  <div class="docs-i18n-page">
    <div class="page-header">
      <h1>多语言文档</h1>
      <p>QooBot 文档支持中文、英文、日文、韩文、德文——社区翻译贡献，全球化覆盖</p>
    </div>

    <el-row :gutter="24">
      <el-col :span="16">
        <div class="page-card">
          <h2>🌐 当前语言覆盖</h2>
          <el-table :data="languages" stripe style="margin-top: 16px">
            <el-table-column prop="lang" label="语言" width="140" />
            <el-table-column prop="code" label="代码" width="80" />
            <el-table-column prop="progress" label="翻译进度" width="200">
              <template #default="{ row }">
                <el-progress :percentage="row.progress" :status="row.progress === 100 ? 'success' : ''" />
              </template>
            </el-table-column>
            <el-table-column prop="maintainers" label="维护者" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" @click="switchLang(row.code)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="page-card" style="margin-top: 20px">
          <h2>🤝 参与翻译贡献</h2>
          <el-steps :active="1" align-center style="margin: 20px 0">
            <el-step title="加入翻译团队" description="申请成为译者" />
            <el-step title="选择待翻译文档" description="从翻译平台认领" />
            <el-step title="提交翻译" description="翻译并提交 Review" />
            <el-step title="审核发布" description="审核通过后自动发布" />
          </el-steps>
          <div style="margin-top: 20px; padding: 16px; background: #f0f9ff; border-radius: 8px">
            <h4 style="margin-bottom: 8px">翻译规范</h4>
            <ul style="line-height: 2; padding-left: 20px; color: var(--qoo-text-secondary)">
              <li>技术术语保持原文，首次出现添加中文注释</li>
              <li>代码块不翻译，仅翻译注释和说明文字</li>
              <li>保持原文的 Markdown 结构和格式</li>
              <li>提交前进行术语一致性检查</li>
            </ul>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card">
          <h3>📊 翻译统计</h3>
          <el-statistic title="总词条数" :value="28500" style="margin-bottom: 16px" />
          <el-statistic title="活跃译者" :value="127" style="margin-bottom: 16px" />
          <el-statistic title="本月新增翻译" :value="3420" />
        </div>
        <div class="page-card" style="margin-top: 16px">
          <h3>🏆 本月翻译贡献榜</h3>
          <ol style="line-height: 2.5; padding-left: 20px">
            <li v-for="c in topContributors" :key="c.name">
              {{ c.name }} <span style="color: var(--qoo-text-secondary); font-size: 13px">— {{ c.words }} 词</span>
            </li>
          </ol>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'

const languages = [
  { lang: '简体中文', code: 'zh-CN', progress: 100, maintainers: '@zhangwei, @liming' },
  { lang: 'English', code: 'en-US', progress: 100, maintainers: '@johndoe, @janedoe' },
  { lang: '日本語', code: 'ja-JP', progress: 85, maintainers: '@tanaka, @suzuki' },
  { lang: '한국어', code: 'ko-KR', progress: 62, maintainers: '@parkjs, @kimsh' },
  { lang: 'Deutsch', code: 'de-DE', progress: 45, maintainers: '@mueller, @schmidt' },
]

const topContributors = [
  { name: '@tanaka_hiro', words: 5200 },
  { name: '@park_js_dev', words: 3800 },
  { name: '@mueller_dev', words: 2900 },
  { name: '@suzuki_ken', words: 2100 },
  { name: '@kim_translate', words: 1800 },
]

const switchLang = (code: string) => ElMessage.success(`已切换到 ${code} 版本`)
</script>

<style lang="scss" scoped>
h2 { font-size: 20px; }
h3 { font-size: 16px; margin-bottom: 8px; }
</style>
