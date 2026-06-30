<template>
  <div class="docs-search-page">
    <div class="page-header">
      <h1>搜索与导航</h1>
      <p>全文搜索 QooBot 全部文档、论坛、问答、博客内容</p>
    </div>

    <div class="page-card search-hero">
      <el-input v-model="query" size="large" placeholder="搜索文档、API、教程、论坛帖子..." clearable
        :prefix-icon="Search" @keyup.enter="doSearch" class="search-input">
        <template #append>
          <el-button type="primary" @click="doSearch" :loading="searching">搜索</el-button>
        </template>
      </el-input>
      <div class="search-tips" v-if="!hasSearched">
        <el-tag v-for="tag in hotTags" :key="tag" @click="query = tag; doSearch()" style="cursor: pointer; margin: 4px">
          {{ tag }}
        </el-tag>
      </div>
    </div>

    <div v-if="hasSearched" style="margin-top: 20px">
      <div class="search-meta" style="margin-bottom: 16px; color: var(--qoo-text-secondary)">
        找到 <strong>{{ results.length }}</strong> 条结果，用时 {{ searchTime }}ms
        <el-radio-group v-model="filterType" size="small" style="margin-left: 16px">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="docs">文档</el-radio-button>
          <el-radio-button label="forum">论坛</el-radio-button>
          <el-radio-button label="qa">问答</el-radio-button>
          <el-radio-button label="blog">博客</el-radio-button>
        </el-radio-group>
      </div>

      <div v-for="result in filteredResults" :key="result.id" class="page-card search-result" @click="goTo(result)">
        <div class="result-header">
          <el-tag size="small" :type="typeTag(result.type)">{{ result.type }}</el-tag>
          <h3>{{ result.title }}</h3>
        </div>
        <p class="result-snippet" v-html="result.snippet"></p>
        <div class="result-meta">
          <span>{{ result.path }}</span>
          <span>{{ result.date }}</span>
        </div>
      </div>

      <el-empty v-if="filteredResults.length === 0" description="未找到匹配结果" />
    </div>

    <div v-else class="page-card" style="margin-top: 20px">
      <h2>📚 快速导航</h2>
      <el-row :gutter="20" style="margin-top: 16px">
        <el-col v-for="nav in quickNavs" :key="nav.title" :span="8" style="margin-bottom: 16px">
          <el-card shadow="hover" class="nav-card" @click="$router.push(nav.path)">
            <el-icon :size="28" style="color: var(--qoo-primary)"><component :is="nav.icon" /></el-icon>
            <h3 style="margin: 8px 0 4px">{{ nav.title }}</h3>
            <p style="font-size: 13px; color: var(--qoo-text-secondary)">{{ nav.desc }}</p>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search, Document, Reading, ChatLineSquare, Notebook, VideoCamera, Link } from '@element-plus/icons-vue'

const query = ref('')
const searching = ref(false)
const hasSearched = ref(false)
const searchTime = ref(0)
const filterType = ref('all')
const results = ref<any[]>([])

const hotTags = ['行为树', 'SLAM', 'ROS2', 'YOLO', '阻抗控制', 'Docker', 'API Key', 'OTA升级']

const quickNavs = [
  { title: 'API 文档', desc: 'Python/C++ SDK 参考', path: '/docs/api', icon: Document },
  { title: '入门教程', desc: '从零开始搭建机器人', path: '/academy', icon: Reading },
  { title: '技术论坛', desc: '讨论与交流', path: '/forums', icon: ChatLineSquare },
  { title: '技术博客', desc: '深度技术文章', path: '/blog', icon: Notebook },
  { title: '示例库', desc: '可运行的代码示例', path: '/docs/examples', icon: VideoCamera },
  { title: '问答社区', desc: '技术问题求助', path: '/qa', icon: Link },
]

const filteredResults = computed(() => {
  if (filterType.value === 'all') return results.value
  return results.value.filter((r: any) => r.type === filterType.value)
})

const typeTag = (type: string) => ({ docs: 'primary', forum: 'success', qa: 'warning', blog: 'info' }[type] as any)

const doSearch = () => {
  if (!query.value.trim()) return
  searching.value = true
  setTimeout(() => {
    results.value = [
      { id: 1, type: 'docs', title: 'qoobot.perception.Camera API 参考', snippet: 'Camera 类提供对 RGB 和深度相机的统一访问接口。支持 <em>YOLO</em> 目标检测模型...', path: 'docs/api/python-perception', date: '2026-06-15' },
      { id: 2, type: 'forum', title: '如何使用行为树引擎编排复杂任务？', snippet: '行为树引擎支持 <em>Sequence</em>、Selector、Parallel 等节点类型...', path: 'forums/t/123', date: '2026-06-20' },
      { id: 3, type: 'qa', title: 'LiDAR 点云数据如何与视觉融合？', snippet: '推荐使用 sensor_fusion 模块的 MultiModalFuser...', path: 'qa/q/456', date: '2026-06-18' },
      { id: 4, type: 'blog', title: '深入理解阻抗控制器参数调优', snippet: '刚度参数 <em>K</em> 决定了机器人对外力的响应...', path: 'blog/impedance-tuning', date: '2026-06-10' },
    ]
    searchTime.value = 32
    searching.value = false
    hasSearched.value = true
  }, 500)
}

const goTo = (result: any) => {
  // navigate to result
}
</script>

<style lang="scss" scoped>
.search-hero { text-align: center; padding: 32px; }
.search-input { max-width: 640px; }
.search-tips { margin-top: 16px; }
.search-result { cursor: pointer; transition: box-shadow .2s;
  &:hover { box-shadow: 0 4px 16px rgba(0,0,0,.12); }
}
.result-header { display: flex; align-items: center; gap: 8px;
  h3 { font-size: 17px; }
}
.result-snippet { margin: 8px 0; color: var(--qoo-text-secondary); line-height: 1.6; }
.result-meta { display: flex; gap: 16px; font-size: 12px; color: var(--qoo-text-secondary); }
.nav-card { cursor: pointer; transition: transform .2s;
  &:hover { transform: translateY(-2px); }
}
h2 { font-size: 20px; }
</style>
