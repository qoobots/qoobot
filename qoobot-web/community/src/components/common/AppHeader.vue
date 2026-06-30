<template>
  <header class="app-header">
    <div class="header-inner">
      <router-link to="/" class="logo">
        <span class="logo-icon">🤖</span>
        <span class="logo-text">QooBot Community</span>
      </router-link>

      <nav class="nav-links">
        <el-dropdown trigger="hover" popper-class="nav-dropdown">
          <span class="nav-link nav-link-dropdown">文档 <el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/docs/api')">API 文档</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/docs/examples')">示例库</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/docs/playground')">Playground</el-dropdown-item>
              <el-dropdown-item divided @click="$router.push('/docs/versions')">版本化文档</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/docs/i18n')">多语言</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/docs/search')">搜索</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <router-link to="/forums" class="nav-link">论坛</router-link>
        <router-link to="/qa" class="nav-link">问答</router-link>
        <el-dropdown trigger="hover" popper-class="nav-dropdown">
          <span class="nav-link nav-link-dropdown">社区 <el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/community/groups')">用户组</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/community/chat')">即时通讯</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/community/feedback')">反馈渠道</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <router-link to="/events" class="nav-link">活动</router-link>
        <el-dropdown trigger="hover" popper-class="nav-dropdown">
          <span class="nav-link nav-link-dropdown">学院 <el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/academy')">课程中心</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/academy/learning-paths')">学习路径</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/academy/cert')">认证中心</el-dropdown-item>
              <el-dropdown-item divided @click="$router.push('/academy/university')">高校合作</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/academy/lab-sponsorship')">实验室赞助</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/academy/internship')">实习计划</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <router-link to="/blog" class="nav-link">博客</router-link>
        <router-link to="/showcase" class="nav-link">案例</router-link>
        <el-dropdown trigger="hover" popper-class="nav-dropdown">
          <span class="nav-link nav-link-dropdown">贡献者 <el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/contributors')">贡献者墙</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/contributors/levels')">等级体系</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/contributors/cla')">CLA 签署</el-dropdown-item>
              <el-dropdown-item divided @click="$router.push('/contributors/standards')">代码规范</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/contributors/pr-guide')">PR 流程</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/contributors/good-first-issues')">新手任务</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown class="nav-dropdown" trigger="hover">
          <span class="nav-link nav-link-dropdown">治理 <el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/governance/charter')">社区宪章</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/governance/tsc-sig')">治理结构</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/governance/rfcs')">RFC 提案</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/governance/roadmap')">路线图</el-dropdown-item>
              <el-dropdown-item divided @click="$router.push('/governance/transparency')">透明度报告</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/governance/conflict')">冲突调解</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown class="nav-dropdown" trigger="hover">
          <span class="nav-link nav-link-dropdown">媒体 <el-icon><ArrowDown /></el-icon></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/content/videos')">视频内容</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/content/social')">社交媒体</el-dropdown-item>
              <el-dropdown-item @click="$router.push('/content/brand')">品牌资产</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </nav>

      <div class="header-actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索..."
          size="small"
          class="search-input"
          @keyup.enter="doSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <template v-if="userStore.isLoggedIn">
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32">{{ userStore.nickname.charAt(0) }}</el-avatar>
              <span class="nickname">{{ userStore.nickname }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/dashboard/profile')">个人资料</el-dropdown-item>
                <el-dropdown-item @click="$router.push('/dashboard/courses')">我的课程</el-dropdown-item>
                <el-dropdown-item divided @click="userStore.logout()">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <el-button v-else type="primary" size="small" @click="mockLogin">登录</el-button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, ArrowDown } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const searchQuery = ref('')

function doSearch() {
  if (searchQuery.value.trim()) {
    router.push({ path: '/docs/search', query: { q: searchQuery.value } })
  }
}

function mockLogin() {
  userStore.login('demo_user', '社区成员', '')
}
</script>

<style lang="scss" scoped>
.app-header {
  background: #fff;
  border-bottom: 1px solid var(--qoo-border);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 56px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none !important;
  margin-right: 32px;

  .logo-icon { font-size: 24px; }
  .logo-text { font-size: 16px; font-weight: 700; color: var(--qoo-text); }
}

.nav-links {
  display: flex;
  gap: 4px;
  flex: 1;
}

.nav-link {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 14px;
  color: var(--qoo-text-secondary);
  text-decoration: none !important;
  transition: all 0.2s;

  &:hover, &.router-link-active {
    color: var(--qoo-primary);
    background: rgba(74, 144, 217, 0.08);
  }
}

.nav-link-dropdown {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.nav-dropdown {
  :deep(.el-dropdown-menu__item) {
    font-size: 14px;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;

  .search-input { width: 200px; }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;

  .nickname {
    font-size: 14px;
    color: var(--qoo-text);
  }
}
</style>
