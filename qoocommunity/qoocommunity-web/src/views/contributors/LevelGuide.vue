<template>
  <div class="level-guide">
    <div class="page-header">
      <h1>贡献者等级体系</h1>
      <p>了解 QooBot 社区的贡献者晋升路径与权益</p>
    </div>

    <div class="level-grid">
      <div v-for="level in levels" :key="level.name" class="page-card level-card">
        <div class="level-icon">{{ level.icon }}</div>
        <h3 class="level-name">{{ level.label }}</h3>
        <el-tag :type="level.tagType" size="small">{{ level.name }}</el-tag>
        <p class="level-desc">{{ level.description }}</p>

        <div class="level-section">
          <h4>晋升要求</h4>
          <ul>
            <li v-for="req in level.requirements" :key="req">{{ req }}</li>
          </ul>
        </div>

        <div class="level-section">
          <h4>等级权益</h4>
          <ul>
            <li v-for="benefit in level.benefits" :key="benefit">{{ benefit }}</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="page-card level-footer">
      <h3>如何开始贡献？</h3>
      <p>访问我们的 <router-link to="/contributors">贡献者墙</router-link> 了解更多，或查看 <a href="https://github.com/qoobot/qoobot" target="_blank">GitHub 仓库</a> 的 Good First Issues。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
interface LevelInfo {
  name: string
  label: string
  icon: string
  tagType: string
  description: string
  requirements: string[]
  benefits: string[]
}

const levels: LevelInfo[] = [
  {
    name: 'NOVICE',
    label: '新手',
    icon: '\u{1F530}',
    tagType: 'info',
    description: '欢迎加入 QooBot 社区！新手是每位贡献者的起点，您可以自由浏览和参与社区讨论。',
    requirements: [
      '注册 QooBot Community 账号',
      '阅读并同意社区行为准则'
    ],
    benefits: [
      '浏览论坛和问答内容',
      '参与社区讨论和提问',
      '查看技术博客和案例'
    ]
  },
  {
    name: 'CONTRIBUTOR',
    label: '贡献者',
    icon: '\u{1F331}',
    tagType: 'success',
    description: '通过代码或文档贡献，正式成为 QooBot 的贡献者，参与项目开发。',
    requirements: [
      '签署 CLA 贡献者许可协议',
      '提交至少 1 个 PR 并被合并',
      '遵守代码规范和提交流程'
    ],
    benefits: [
      '参与项目代码开发',
      '在贡献者墙上展示',
      '获得社区贡献徽章',
      '访问内部开发者讨论区'
    ]
  },
  {
    name: 'MAINTAINER',
    label: '维护者',
    icon: '\u{2B50}',
    tagType: 'warning',
    description: '持续贡献并获得社区认可的成员，可管理特定模块的代码评审和合并。',
    requirements: [
      '持续贡献 3 个月以上',
      '累计合并 PR 达到 10 个',
      '获得至少 2 名现有维护者推荐',
      '通过社区投票'
    ],
    benefits: [
      '管理特定模块的 PR 评审',
      '合并代码权限',
      '参与技术决策讨论',
      '优先获得社区资源支持',
      '社区活动嘉宾邀请资格'
    ]
  },
  {
    name: 'COMMITTER',
    label: '提交者',
    icon: '\u{1F451}',
    tagType: 'danger',
    description: 'QooBot 核心贡献者，拥有对项目核心代码的提交权限，参与社区重大决策。',
    requirements: [
      '作为维护者活跃 6 个月以上',
      '对项目架构有深入理解',
      '累计合并 PR 达到 50 个',
      '通过 Committer 选举投票',
      '获得技术委员会批准'
    ],
    benefits: [
      '核心代码提交权限',
      '参与技术委员会决策',
      '项目路线图制定权',
      'QooBot 官方技术大使称号',
      '获得项目赞助和差旅支持',
      'GitHub 组织 Owner 权限'
    ]
  }
]
</script>

<style lang="scss" scoped>
.level-guide {
  max-width: 1000px;
  margin: 0 auto;
}

.level-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.level-card {
  display: flex;
  flex-direction: column;

  .level-icon {
    font-size: 40px;
    margin-bottom: 12px;
  }

  .level-name {
    font-size: 18px;
    font-weight: 600;
    color: var(--qoo-text);
    margin-bottom: 8px;
  }

  .level-desc {
    font-size: 14px;
    color: var(--qoo-text-secondary);
    line-height: 1.6;
    margin: 12px 0;
  }
}

.level-section {
  margin-top: 12px;

  h4 {
    font-size: 13px;
    font-weight: 600;
    color: var(--qoo-primary);
    margin-bottom: 6px;
  }

  ul {
    list-style: none;
    padding: 0;

    li {
      font-size: 13px;
      color: var(--qoo-text-secondary);
      line-height: 1.8;
      padding-left: 16px;
      position: relative;

      &::before {
        content: '\2022';
        position: absolute;
        left: 0;
        color: var(--qoo-primary);
      }
    }
  }
}

.level-footer {
  text-align: center;

  h3 {
    margin-bottom: 8px;
    font-size: 16px;
  }

  p {
    font-size: 14px;
    color: var(--qoo-text-secondary);
  }

  a {
    color: var(--qoo-primary);
  }
}
</style>
