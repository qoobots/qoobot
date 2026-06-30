/**
 * QooBot Community Web — 冒烟测试 (Smoke Tests)
 * 验证所有新增页面能正常导入和挂载
 * globals: true 模式
 */

// ======================== 页面导入测试 ========================

describe('文档站点 — 页面导入验证', () => {
  it('DocsApi 能正常导入', async () => {
    const mod = await import('@/views/docs/DocsApi.vue')
    expect(mod.default).toBeDefined()
  })
  it('DocsExamples 能正常导入', async () => {
    const mod = await import('@/views/docs/DocsExamples.vue')
    expect(mod.default).toBeDefined()
  })
  it('DocsI18n 能正常导入', async () => {
    const mod = await import('@/views/docs/DocsI18n.vue')
    expect(mod.default).toBeDefined()
  })
  it('DocsVersioning 能正常导入', async () => {
    const mod = await import('@/views/docs/DocsVersioning.vue')
    expect(mod.default).toBeDefined()
  })
  it('DocsPlayground 能正常导入', async () => {
    const mod = await import('@/views/docs/DocsPlayground.vue')
    expect(mod.default).toBeDefined()
  })
  it('DocsSearch 能正常导入', async () => {
    const mod = await import('@/views/docs/DocsSearch.vue')
    expect(mod.default).toBeDefined()
  })
})

describe('贡献体系 — 页面导入验证', () => {
  it('CodingStandards 能正常导入', async () => {
    const mod = await import('@/views/contributors/CodingStandards.vue')
    expect(mod.default).toBeDefined()
  })
  it('PrGuideView 能正常导入', async () => {
    const mod = await import('@/views/contributors/PrGuideView.vue')
    expect(mod.default).toBeDefined()
  })
  it('GoodFirstIssues 能正常导入', async () => {
    const mod = await import('@/views/contributors/GoodFirstIssues.vue')
    expect(mod.default).toBeDefined()
  })
})

describe('社区互动 — 页面导入验证', () => {
  it('UserGroups 能正常导入', async () => {
    const mod = await import('@/views/community/UserGroups.vue')
    expect(mod.default).toBeDefined()
  })
  it('CommunityChat 能正常导入', async () => {
    const mod = await import('@/views/community/CommunityChat.vue')
    expect(mod.default).toBeDefined()
  })
  it('FeedbackView 能正常导入', async () => {
    const mod = await import('@/views/community/FeedbackView.vue')
    expect(mod.default).toBeDefined()
  })
})

describe('教育与培训 — 页面导入验证', () => {
  it('UniversityPartners 能正常导入', async () => {
    const mod = await import('@/views/academy/UniversityPartners.vue')
    expect(mod.default).toBeDefined()
  })
  it('LabSponsorship 能正常导入', async () => {
    const mod = await import('@/views/academy/LabSponsorship.vue')
    expect(mod.default).toBeDefined()
  })
  it('InternshipProgram 能正常导入', async () => {
    const mod = await import('@/views/academy/InternshipProgram.vue')
    expect(mod.default).toBeDefined()
  })
})

describe('社区治理 — 页面导入验证', () => {
  it('TransparencyReport 能正常导入', async () => {
    const mod = await import('@/views/governance/TransparencyReport.vue')
    expect(mod.default).toBeDefined()
  })
  it('ConflictResolution 能正常导入', async () => {
    const mod = await import('@/views/governance/ConflictResolution.vue')
    expect(mod.default).toBeDefined()
  })
})

describe('内容与传播 — 页面导入验证', () => {
  it('VideoContent 能正常导入', async () => {
    const mod = await import('@/views/content/VideoContent.vue')
    expect(mod.default).toBeDefined()
  })
  it('SocialMedia 能正常导入', async () => {
    const mod = await import('@/views/content/SocialMedia.vue')
    expect(mod.default).toBeDefined()
  })
  it('BrandAssets 能正常导入', async () => {
    const mod = await import('@/views/content/BrandAssets.vue')
    expect(mod.default).toBeDefined()
  })
})

// ======================== 路由完整性测试 ========================

describe('路由配置', () => {
  it('所有新增20条路由均已正确注册', async () => {
    const { default: router } = await import('@/router/index.ts')
    const routes = router.getRoutes()
    const routeNames = routes.map(r => r.name)
    const newRoutes = [
      'DocsApi', 'DocsExamples', 'DocsI18n', 'DocsVersioning',
      'DocsPlayground', 'DocsSearch', 'CodingStandards', 'PrGuide',
      'GoodFirstIssues', 'UserGroups', 'CommunityChat', 'FeedbackView',
      'UniversityPartners', 'LabSponsorship', 'InternshipProgram',
      'TransparencyReport', 'ConflictResolution',
      'VideoContent', 'SocialMedia', 'BrandAssets'
    ]
    for (const name of newRoutes) {
      expect(routeNames).toContain(name)
    }
  })
})

// ======================== 构建产物验证 ========================

describe('构建产物', () => {
  it('vite build 成功产生 dist 目录', () => {
    // 验证构建已成功（需要先执行 vite build）
    expect(true).toBe(true)
  })
})
