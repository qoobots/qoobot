<template>
  <div class="feedback-page">
    <div class="page-header">
      <h1>反馈渠道</h1>
      <p>功能请求投票、Bug 报告、用户反馈收集——你的声音塑造 QooBot 的未来</p>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="功能请求" name="feature">
        <div class="page-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
            <h2>💡 功能请求投票</h2>
            <el-button type="primary" @click="showFeatureDialog = true">提交新请求</el-button>
          </div>
          <el-table :data="featureRequests" stripe @row-click="(row: any) => voteFeature(row)">
            <el-table-column prop="title" label="功能" min-width="280" />
            <el-table-column prop="category" label="分类" width="120">
              <template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template>
            </el-table-column>
            <el-table-column label="投票" width="140">
              <template #default="{ row }">
                <el-button size="small" :type="row.voted ? 'primary' : 'default'" @click.stop="toggleVote(row)">
                  <el-icon><CaretTop /></el-icon> {{ row.votes }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
      <el-tab-pane label="Bug 报告" name="bug">
        <div class="page-card">
          <el-form :model="bugForm" label-width="100px" label-position="top">
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="标题">
                  <el-input v-model="bugForm.title" placeholder="简要描述 Bug" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="影响版本">
                  <el-select v-model="bugForm.version" placeholder="选择版本">
                    <el-option label="v2.1.0" value="v2.1.0" />
                    <el-option label="v2.0.0 LTS" value="v2.0.0" />
                    <el-option label="v1.0.0" value="v1.0.0" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="复现步骤">
              <el-input v-model="bugForm.steps" type="textarea" :rows="3" placeholder="详细描述复现步骤" />
            </el-form-item>
            <el-form-item label="期望行为">
              <el-input v-model="bugForm.expected" type="textarea" :rows="2" placeholder="描述期望的正确行为" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="submitBug">提交 Bug 报告</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
      <el-tab-pane label="用户反馈" name="general">
        <div class="page-card">
          <el-form :model="generalForm" label-position="top">
            <el-form-item label="反馈类型">
              <el-radio-group v-model="generalForm.type">
                <el-radio-button label="建议">改进建议</el-radio-button>
                <el-radio-button label="问题">使用问题</el-radio-button>
                <el-radio-button label="体验">体验反馈</el-radio-button>
                <el-radio-button label="其他">其他</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="反馈内容">
              <el-input v-model="generalForm.content" type="textarea" :rows="4" placeholder="请详细描述你的反馈..." />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="submitGeneral">提交反馈</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showFeatureDialog" title="提交功能请求" width="520px">
      <el-form :model="newFeature" label-position="top">
        <el-form-item label="功能标题">
          <el-input v-model="newFeature.title" placeholder="简明扼要地描述你希望添加的功能" />
        </el-form-item>
        <el-form-item label="详细描述">
          <el-input v-model="newFeature.desc" type="textarea" :rows="3" placeholder="描述功能的使用场景和预期效果" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="newFeature.category">
            <el-option label="感知模块" value="感知" />
            <el-option label="导航模块" value="导航" />
            <el-option label="控制模块" value="控制" />
            <el-option label="AI 推理" value="AI" />
            <el-option label="开发者工具" value="工具" />
            <el-option label="文档" value="文档" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFeatureDialog = false">取消</el-button>
        <el-button type="primary" @click="submitFeature">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { CaretTop } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('feature')
const showFeatureDialog = ref(false)

const featureRequests = ref([
  { id: 1, title: '支持 ROS 2 Humble 完整兼容', category: '控制', votes: 342, voted: false, status: '已采纳' },
  { id: 2, title: 'Web 端 3D 机器人可视化', category: '工具', votes: 287, voted: false, status: '评估中' },
  { id: 3, title: '移动端 SDK (React Native)', category: '工具', votes: 198, voted: false, status: '规划中' },
  { id: 4, title: '技能市场用户评分系统', category: 'AI', votes: 156, voted: false, status: '已采纳' },
])

const bugForm = reactive({ title: '', version: '', steps: '', expected: '' })
const generalForm = reactive({ type: '建议', content: '' })
const newFeature = reactive({ title: '', desc: '', category: '' })

const statusType = (s: string) => ({ '已采纳': 'success', '评估中': 'warning', '规划中': 'info' }[s] as any)
const toggleVote = (row: any) => { row.voted = !row.voted; row.votes += row.voted ? 1 : -1 }
const voteFeature = (row: any) => {}
const submitBug = () => ElMessage.success('Bug 报告已提交')
const submitGeneral = () => ElMessage.success('反馈已提交')
const submitFeature = () => { showFeatureDialog.value = false; ElMessage.success('功能请求已提交') }
</script>

<style lang="scss" scoped>
h2 { font-size: 20px; }
</style>
