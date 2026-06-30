<template>
  <div class="user-groups-page">
    <div class="page-header">
      <h1>用户组</h1>
      <p>加入本地 QooBot 开发者用户组——城市/高校/行业用户组、线下聚会、线上 Meetup</p>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="城市用户组" name="city">
        <el-row :gutter="20">
          <el-col v-for="group in cityGroups" :key="group.name" :xs="24" :sm="12" :md="8" style="margin-bottom: 16px">
            <el-card class="group-card" shadow="hover">
              <div class="group-header">
                <el-avatar :size="48" :style="{ background: group.color }">{{ group.name[0] }}</el-avatar>
                <div>
                  <h3>{{ group.name }}</h3>
                  <span style="font-size: 13px; color: var(--qoo-text-secondary)">{{ group.members }} 成员</span>
                </div>
              </div>
              <p style="margin: 12px 0; font-size: 13px; color: var(--qoo-text-secondary); line-height: 1.6">{{ group.desc }}</p>
              <div class="group-footer">
                <span><el-icon><Calendar /></el-icon> {{ group.nextEvent }}</span>
                <el-button type="primary" size="small" link>加入</el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
      <el-tab-pane label="高校用户组" name="university">
        <el-table :data="uniGroups" stripe>
          <el-table-column prop="name" label="高校" width="200" />
          <el-table-column prop="leader" label="负责人" width="120" />
          <el-table-column prop="members" label="成员数" width="100" />
          <el-table-column prop="activity" label="近期活动" min-width="200" />
          <el-table-column label="操作" width="100">
            <template><el-button size="small" link type="primary">查看</el-button></template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="行业用户组" name="industry">
        <el-table :data="industryGroups" stripe>
          <el-table-column prop="name" label="行业" width="200" />
          <el-table-column prop="focus" label="关注方向" min-width="250" />
          <el-table-column prop="members" label="成员数" width="100" />
          <el-table-column label="操作" width="100">
            <template><el-button size="small" link type="primary">加入</el-button></template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Calendar } from '@element-plus/icons-vue'

const activeTab = ref('city')

const cityGroups = [
  { name: '北京', members: 1280, desc: '北京及华北地区 QooBot 开发者社群，每月举办线下技术分享和黑客松活动。', nextEvent: '7月15日 线下聚会', color: '#e74c3c' },
  { name: '上海', members: 960, desc: '华东地区核心用户组，聚焦机器人应用落地和工业场景。', nextEvent: '7月22日 技术沙龙', color: '#3498db' },
  { name: '深圳', members: 1120, desc: '华南硬件创新中心，侧重机器人硬件开发和供应链交流。', nextEvent: '7月8日 Hackathon', color: '#2ecc71' },
  { name: '杭州', members: 540, desc: 'AI + 机器人交叉领域，定期举办学术交流和产业对接。', nextEvent: '8月5日 Workshop', color: '#9b59b6' },
  { name: '成都', members: 380, desc: '西部开发者社群，涵盖教育和科研应用场景。', nextEvent: '8月12日 Meetup', color: '#e67e22' },
  { name: '东京', members: 620, desc: '日本 QooBot 开发者社区，聚焦服务机器人和人机交互。', nextEvent: '7月20日 勉強会', color: '#1abc9c' },
]

const uniGroups = [
  { name: '清华大学', leader: '@zhangwei', members: 85, activity: 'QooBot 机器人创新大赛' },
  { name: '北京大学', leader: '@lixue', members: 62, activity: '仿生机器人研讨会' },
  { name: '上海交通大学', leader: '@wangfang', members: 78, activity: 'SLAM 技术分享会' },
  { name: '浙江大学', leader: '@chenjie', members: 55, activity: '机器人控制算法 Workshop' },
]

const industryGroups = [
  { name: '智能制造', focus: '工业机器人、自动化产线、质量检测', members: 450 },
  { name: '服务机器人', focus: '酒店/餐饮/医疗/养老机器人应用', members: 380 },
  { name: '教育培训', focus: '机器人课程建设、竞赛培训、STEM 教育', members: 290 },
  { name: '物流仓储', focus: 'AGV/AMR、仓储自动化、最后一公里配送', members: 320 },
]
</script>

<style lang="scss" scoped>
.group-card { transition: transform .2s; &:hover { transform: translateY(-2px); } }
.group-header { display: flex; align-items: center; gap: 12px;
  h3 { font-size: 16px; }
}
.group-footer { display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: var(--qoo-text-secondary); }
</style>
