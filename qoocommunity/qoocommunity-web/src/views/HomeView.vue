<template>
  <div class="home-view">
    <section class="hero-banner">
      <h1>QooBot 开发者社区</h1>
      <p class="hero-subtitle">加入全球人形机器人开发者社区，学习、分享、创造</p>
      <div class="hero-actions">
        <el-button type="primary" size="large" @click="$router.push('/academy')">开始学习</el-button>
        <el-button size="large" @click="$router.push('/forums')">浏览论坛</el-button>
      </div>
      <div class="hero-stats">
        <div class="stat-item">
          <span class="stat-number">5,000+</span>
          <span class="stat-label">开发者</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">1,200+</span>
          <span class="stat-label">技能</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">500+</span>
          <span class="stat-label">帖子</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">50+</span>
          <span class="stat-label">高校</span>
        </div>
      </div>
    </section>

    <div class="home-grid">
      <section class="home-section">
        <div class="section-header">
          <h2>🔥 热门讨论</h2>
          <el-button text type="primary" @click="$router.push('/forums')">查看全部</el-button>
        </div>
        <div class="topic-list">
          <div v-for="i in 5" :key="i" class="topic-item" @click="$router.push('/forums/t/1')">
            <div class="topic-title">如何开始第一个 QooBot 技能开发？</div>
            <div class="topic-meta">
              <span>📦 技能分享</span>
              <span>💬 12 回复</span>
              <span>👍 28 赞</span>
            </div>
          </div>
        </div>
      </section>

      <section class="home-section">
        <div class="section-header">
          <h2>📅 近期活动</h2>
          <el-button text type="primary" @click="$router.push('/events')">查看全部</el-button>
        </div>
        <div class="event-list">
          <div v-for="i in 3" :key="i" class="event-item" @click="$router.push('/events/1')">
            <div class="event-date">7月15日</div>
            <div>
              <div class="event-title">QooBot 2026 夏季黑客松</div>
              <div class="event-location">🌐 线上</div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <section class="home-section">
      <div class="section-header">
        <h2>🎓 学习路径</h2>
      </div>
      <div class="learning-paths">
        <div v-for="path in learningPaths" :key="path.title" class="path-card" @click="$router.push('/academy')">
          <div class="path-icon">{{ path.icon }}</div>
          <div class="path-title">{{ path.title }}</div>
          <div class="path-desc">{{ path.desc }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const learningPaths = ref([
  { icon: '🔧', title: '硬件组装', desc: '从零部件到完整机器人' },
  { icon: '💻', title: '系统烧录', desc: '安装 qoobrain 操作系统' },
  { icon: '📖', title: 'SDK 入门', desc: 'Python/C++ SDK 快速上手' },
  { icon: '🎯', title: '技能开发', desc: '行为树编程与技能创建' },
  { icon: '🚀', title: '高级集成', desc: '感知、规划、控制系统' },
  { icon: '🎓', title: '认证考试', desc: '获取 QooBot 开发者认证' }
])
</script>

<style lang="scss" scoped>
.hero-banner {
  background: linear-gradient(135deg, #1A1A2E 0%, #4A90D9 100%);
  color: #fff;
  text-align: center;
  padding: 64px 20px;
  border-radius: 16px;
  margin-bottom: 32px;

  h1 { font-size: 36px; font-weight: 800; margin-bottom: 12px; }
  .hero-subtitle { font-size: 18px; opacity: 0.85; margin-bottom: 28px; }
  .hero-actions { display: flex; gap: 12px; justify-content: center; margin-bottom: 40px; }
}

.hero-stats {
  display: flex;
  justify-content: center;
  gap: 48px;
}

.stat-item {
  text-align: center;

  .stat-number { display: block; font-size: 24px; font-weight: 700; }
  .stat-label { font-size: 13px; opacity: 0.7; }
}

.home-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 32px;
}

.home-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: var(--qoo-shadow);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;

  h2 { font-size: 18px; font-weight: 600; }
}

.topic-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--qoo-border);
  cursor: pointer;

  &:last-child { border-bottom: none; }

  .topic-title {
    font-size: 15px;
    font-weight: 500;
    margin-bottom: 6px;

    &:hover { color: var(--qoo-primary); }
  }

  .topic-meta {
    font-size: 12px;
    color: var(--qoo-text-secondary);
    display: flex;
    gap: 16px;
  }
}

.event-item {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid var(--qoo-border);
  cursor: pointer;

  &:last-child { border-bottom: none; }

  .event-date {
    background: var(--qoo-primary);
    color: #fff;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    white-space: nowrap;
    align-self: flex-start;
  }

  .event-title { font-size: 15px; font-weight: 500; }
  .event-location { font-size: 12px; color: var(--qoo-text-secondary); margin-top: 4px; }
}

.learning-paths {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.path-card {
  padding: 20px;
  border: 1px solid var(--qoo-border);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--qoo-primary);
    box-shadow: var(--qoo-shadow);
  }

  .path-icon { font-size: 28px; margin-bottom: 8px; }
  .path-title { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
  .path-desc { font-size: 13px; color: var(--qoo-text-secondary); }
}
</style>
