<template>
  <div class="conflict-resolution-page">
    <div class="page-header">
      <h1>冲突调解</h1>
      <p>社区仲裁机制、违规处理流程、申诉渠道——维护健康友好的社区环境</p>
    </div>

    <el-row :gutter="24">
      <el-col :span="16">
        <div class="page-card">
          <h2>⚖️ 社区行为准则</h2>
          <el-alert type="warning" :closable="false" show-icon style="margin: 16px 0">
            QooBot 社区致力于为每个人提供友好、安全和受欢迎的环境，无论性别、性取向、能力、种族、宗教信仰如何。
          </el-alert>
          <el-collapse>
            <el-collapse-item title="期望行为" name="1">
              <ul style="line-height: 2.2; padding-left: 20px">
                <li>使用友好和包容的语言</li>
                <li>尊重不同的观点和经验</li>
                <li>优雅地接受建设性批评</li>
                <li>关注对社区最有利的事情</li>
                <li>对其他社区成员表现出同理心</li>
              </ul>
            </el-collapse-item>
            <el-collapse-item title="不可接受的行为" name="2">
              <ul style="line-height: 2.2; padding-left: 20px; color: #e74c3c">
                <li>使用性暗示语言或图像</li>
                <li>人身攻击、侮辱性/贬损性评论</li>
                <li>公开或私下骚扰</li>
                <li>未经许可发布他人私人信息</li>
                <li>其他在专业环境中被合理认为不适当的行为</li>
              </ul>
            </el-collapse-item>
          </el-collapse>
        </div>

        <div class="page-card" style="margin-top: 20px">
          <h2>📋 违规处理流程</h2>
          <el-steps :active="3" align-center style="margin: 20px 0">
            <el-step title="事件报告" description="提交违规报告" />
            <el-step title="初步审查" description="24h 内响应" />
            <el-step title="调查取证" description="收集相关证据" />
            <el-step title="裁决通知" description="告知处理结果" />
            <el-step title="申诉处理" description="如有异议可申诉" />
          </el-steps>
          <el-descriptions :column="2" border style="margin-top: 16px">
            <el-descriptions-item label="首次违规">书面警告，说明违反的规则</el-descriptions-item>
            <el-descriptions-item label="二次违规">临时封禁 7 天</el-descriptions-item>
            <el-descriptions-item label="三次违规">临时封禁 30 天</el-descriptions-item>
            <el-descriptions-item label="严重违规">永久封禁，无申诉资格</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="page-card">
          <h3>📬 报告违规</h3>
          <p style="color: var(--qoo-text-secondary); margin: 12px 0; line-height: 1.8">
            如果你目击或遭遇了违反行为准则的行为，请通过以下方式联系我们：
          </p>
          <el-timeline>
            <el-timeline-item>
              <strong>邮件报告</strong>
              <p style="font-size: 13px; color: var(--qoo-text-secondary)">conduct@qoobot.org</p>
            </el-timeline-item>
            <el-timeline-item>
              <strong>Discord ModMail</strong>
              <p style="font-size: 13px; color: var(--qoo-text-secondary)">#mod-report 频道</p>
            </el-timeline-item>
            <el-timeline-item>
              <strong>匿名举报</strong>
              <p style="font-size: 13px; color: var(--qoo-text-secondary)">在线匿名表单</p>
            </el-timeline-item>
          </el-timeline>
          <el-button type="primary" style="margin-top: 16px; width: 100%">提交报告</el-button>
        </div>
        <div class="page-card" style="margin-top: 16px">
          <h3>🛡️ 调解委员会</h3>
          <div v-for="member in committee" :key="member.name" style="display: flex; align-items: center; gap: 10px; padding: 8px 0">
            <el-avatar :size="36">{{ member.name[0] }}</el-avatar>
            <div>
              <div style="font-weight: 500">{{ member.name }}</div>
              <div style="font-size: 12px; color: var(--qoo-text-secondary)">{{ member.role }}</div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
const committee = [
  { name: 'Zhang Wei', role: '委员会主席' },
  { name: 'Li Ming', role: '社区经理' },
  { name: 'Jane Doe', role: '开发者代表' },
  { name: 'Tanaka Hiro', role: '社区代表' },
]
</script>

<style lang="scss" scoped>
h2 { font-size: 20px; }
h3 { font-size: 16px; margin-bottom: 8px; }
</style>
