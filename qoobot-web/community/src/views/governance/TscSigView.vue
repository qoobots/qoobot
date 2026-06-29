<template>
  <div class="tsc-sig-view">
    <div class="page-header">
      <h1>社区治理结构</h1>
      <p>QooBot 技术指导委员会(TSC)与专项兴趣小组(SIG)</p>
    </div>

    <div v-if="loading" class="page-card empty-state">
      <p>加载中...</p>
    </div>

    <template v-else>
      <!-- TSC Section -->
      <section class="section">
        <div class="section-header">
          <h2>技术指导委员会 (TSC)</h2>
          <el-tag v-if="tscMembers.length" type="info" effect="plain">
            共 {{ tscMembers.length }} 名成员
          </el-tag>
        </div>
        <div v-if="tscMembers.length" class="member-grid">
          <el-card v-for="member in tscMembers" :key="member.id" class="member-card" shadow="hover">
            <div class="member-avatar">
              <el-avatar :size="64" :src="member.avatarUrl">
                {{ (member.name || member.nickname).charAt(0) }}
              </el-avatar>
            </div>
            <div class="member-info">
              <div class="member-name">
                {{ member.name || member.nickname }}
                <el-tag :type="roleTagType(member.role)" size="small" class="role-tag">
                  {{ roleLabel(member.role) }}
                </el-tag>
              </div>
              <p v-if="member.bio" class="member-bio">{{ member.bio }}</p>
              <a v-if="member.github" :href="member.github" target="_blank" class="member-github">
                <el-icon><Link /></el-icon>
                GitHub
              </a>
            </div>
          </el-card>
        </div>
        <div v-else class="page-card empty-state">
          <p>暂无 TSC 成员信息</p>
        </div>
      </section>

      <!-- SIG Section -->
      <section class="section">
        <div class="section-header">
          <h2>专项兴趣小组 (SIG)</h2>
          <el-tag v-if="sigs.length" type="info" effect="plain">
            共 {{ sigs.length }} 个小组
          </el-tag>
        </div>
        <div v-if="sigs.length" class="sig-grid">
          <el-card v-for="sig in sigs" :key="sig.id" class="sig-card" shadow="hover">
            <div class="sig-header">
              <h3 class="sig-name">{{ sig.name }}</h3>
              <el-tag v-if="sig.memberCount" type="info" size="small" effect="plain">
                {{ sig.memberCount }} 人
              </el-tag>
              <el-tag :type="sig.isActive ? 'success' : 'info'" size="small" effect="plain">
                {{ sig.isActive ? '活跃' : '非活跃' }}
              </el-tag>
            </div>
            <p v-if="sig.description" class="sig-desc">{{ sig.description }}</p>
            <p v-if="sig.leadName || sig.leads?.length" class="sig-lead">
              负责人：{{ sig.leadName || sig.leads.join('、') }}
            </p>
          </el-card>
        </div>
        <div v-else class="page-card empty-state">
          <p>暂无 SIG 信息</p>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Link } from '@element-plus/icons-vue'
import { governanceApi, type TscMember, type Sig } from '@/api/governance'

const tscMembers = ref<TscMember[]>([])
const sigs = ref<Sig[]>([])
const loading = ref(true)

const roleLabel = (role: string) => {
  const map: Record<string, string> = { CHAIR: '主席', VICE_CHAIR: '副主席', MEMBER: '成员' }
  return map[role] || role
}

const roleTagType = (role: string): 'danger' | 'warning' | 'info' | '' => {
  const map: Record<string, 'danger' | 'warning' | 'info'> = {
    CHAIR: 'danger',
    VICE_CHAIR: 'warning',
    MEMBER: 'info'
  }
  return map[role] || 'info'
}

onMounted(async () => {
  try {
    const [tscRes, sigsRes] = await Promise.all([
      governanceApi.getTscMembers(),
      governanceApi.getSigs()
    ])
    tscMembers.value = tscRes
    sigs.value = sigsRes
  } catch {
    // 加载失败时展示空状态
  } finally {
    loading.value = false
  }
})
</script>

<style lang="scss" scoped>
.section {
  margin-bottom: 40px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;

  h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    color: var(--qoo-text);
  }
}

/* TSC Member Grid */
.member-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.member-card {
  :deep(.el-card__body) {
    display: flex;
    align-items: flex-start;
    gap: 16px;
    padding: 20px;
  }
}

.member-avatar {
  flex-shrink: 0;
}

.member-info {
  flex: 1;
  min-width: 0;
}

.member-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--qoo-text);
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.member-bio {
  font-size: 13px;
  color: var(--qoo-text-secondary);
  line-height: 1.6;
  margin: 0 0 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.member-github {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--qoo-primary);
  text-decoration: none !important;

  &:hover {
    text-decoration: underline !important;
  }
}

/* SIG Grid */
.sig-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.sig-card {
  :deep(.el-card__body) {
    padding: 20px;
  }
}

.sig-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.sig-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--qoo-text);
}

.sig-desc {
  font-size: 14px;
  color: var(--qoo-text-secondary);
  line-height: 1.6;
  margin: 0 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sig-lead {
  font-size: 13px;
  color: var(--qoo-text-secondary);
  margin: 0;
}

.empty-state {
  text-align: center;
  color: var(--qoo-text-secondary);
  padding: 48px;
}
</style>
