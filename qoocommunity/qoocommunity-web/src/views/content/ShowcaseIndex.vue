<template>
  <div class="showcase-index">
    <div class="page-header">
      <h1>案例展示</h1>
      <p>用户成功案例、行业解决方案、创意项目展示</p>
    </div>

    <div class="toolbar">
      <el-tabs v-model="activeCategory">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane v-for="cat in categories" :key="cat" :label="cat" :name="cat" />
      </el-tabs>
      <el-button type="primary" @click="showSubmit = true">提交案例</el-button>
    </div>

    <div class="showcase-grid">
      <div v-for="item in showcases" :key="item.id" class="page-card showcase-card" @click="$router.push(`/showcase/${item.id}`)">
        <div class="showcase-cover" :style="{ background: gradientFor(item.category) }">
          <span class="showcase-category">{{ item.category }}</span>
        </div>
        <div class="showcase-info">
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
          <div class="showcase-meta">
            <span>{{ item.author }}</span>
            <span>{{ item.createdAt }}</span>
          </div>
        </div>
      </div>
    </div>

    <el-pagination
      v-if="total > pageSize"
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      style="margin-top: 24px; justify-content: center"
    />

    <el-dialog v-model="showSubmit" title="提交案例" width="500px">
      <el-form :model="submitForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="submitForm.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="submitForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="submitForm.category" placeholder="选择分类">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="链接">
          <el-input v-model="submitForm.url" placeholder="项目链接（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSubmit = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">提交</el-button>
      </template>
    </el-dialog>

    <div v-if="showcases.length === 0" class="page-card empty-state">
      <p>暂无案例展示</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { contentApi, type Showcase } from '@/api/content'

const showcases = ref<Showcase[]>([])
const categories = ref<string[]>([])
const activeCategory = ref('all')
const currentPage = ref(1)
const pageSize = ref(9)
const total = ref(0)
const showSubmit = ref(false)
const submitForm = ref({ title: '', description: '', category: '', url: '' })

onMounted(async () => {
  await loadShowcases()
})

async function loadShowcases() {
  try {
    const params: any = { page: currentPage.value - 1, size: pageSize.value }
    if (activeCategory.value !== 'all') {
      params.category = activeCategory.value
    }
    const result = await contentApi.getShowcases(params)
    showcases.value = result.content || []
    total.value = result.total || 0
    if (!categories.value.length) {
      categories.value = [...new Set(showcases.value.map(s => s.category))]
    }
  } catch {}
}

async function handleSubmit() {
  try {
    await contentApi.submitShowcase(submitForm.value)
    ElMessage.success('提交成功！')
    showSubmit.value = false
    submitForm.value = { title: '', description: '', category: '', url: '' }
  } catch {}
}

function gradientFor(category: string): string {
  const gradients: Record<string, string> = {
    '机器人': 'linear-gradient(135deg, #667eea, #764ba2)',
    '智能制造': 'linear-gradient(135deg, #f093fb, #f5576c)',
    '科研教育': 'linear-gradient(135deg, #4facfe, #00f2fe)',
    '创客': 'linear-gradient(135deg, #43e97b, #38f9d7)',
    '其他': 'linear-gradient(135deg, #fa709a, #fee140)'
  }
  return gradients[category] || 'linear-gradient(135deg, #4A90D9, #34C759)'
}
</script>

<style lang="scss" scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.showcase-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.showcase-card {
  cursor: pointer;
  overflow: hidden;
  padding: 0;
  transition: transform 0.2s;

  &:hover { transform: translateY(-2px); }

  .showcase-cover {
    height: 100px;
    display: flex;
    align-items: flex-start;
    justify-content: flex-end;
    padding: 12px;
  }

  .showcase-category {
    background: rgba(255,255,255,0.25);
    color: #fff;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
  }

  .showcase-info {
    padding: 16px;

    h3 { font-size: 16px; margin-bottom: 8px; }
    p {
      font-size: 13px;
      color: var(--qoo-text-secondary);
      line-height: 1.5;
      margin-bottom: 8px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .showcase-meta {
      font-size: 12px;
      color: var(--qoo-text-secondary);
      display: flex;
      gap: 12px;
    }
  }
}

.empty-state {
  text-align: center;
  color: var(--qoo-text-secondary);
  padding: 48px;
}
</style>
