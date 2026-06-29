import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory('/qoogear'),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/home/HomePage.vue'),
      meta: { title: 'MFQ 认证门户' },
    },
    // 公开门户
    {
      path: '/certificates',
      name: 'certificates',
      component: () => import('@/views/certificates/CertList.vue'),
      meta: { title: '已认证配件目录' },
    },
    {
      path: '/certificates/:id',
      name: 'certificate-detail',
      component: () => import('@/views/certificates/CertDetail.vue'),
      meta: { title: '认证详情' },
    },
    {
      path: '/standards',
      name: 'standards',
      component: () => import('@/views/standards/StandardList.vue'),
      meta: { title: '接口标准文档' },
    },
    {
      path: '/standards/:id',
      name: 'standard-detail',
      component: () => import('@/views/standards/StandardDetail.vue'),
      meta: { title: '标准详情' },
    },
    // 开发者中心
    {
      path: '/dev',
      name: 'dev-dashboard',
      component: () => import('@/views/developer/DevDashboard.vue'),
      meta: { title: '开发者仪表板', requiresAuth: true },
    },
    {
      path: '/dev/applications',
      name: 'dev-applications',
      component: () => import('@/views/developer/ApplicationList.vue'),
      meta: { title: '我的认证申请', requiresAuth: true },
    },
    {
      path: '/dev/applications/new',
      name: 'dev-application-create',
      component: () => import('@/views/developer/ApplicationCreate.vue'),
      meta: { title: '新建认证申请', requiresAuth: true },
    },
    {
      path: '/dev/applications/:id',
      name: 'dev-application-detail',
      component: () => import('@/views/developer/ApplicationDetail.vue'),
      meta: { title: '申请详情', requiresAuth: true },
    },
    {
      path: '/dev/sdk',
      name: 'dev-sdk',
      component: () => import('@/views/developer/SdkDownload.vue'),
      meta: { title: 'SDK 下载', requiresAuth: true },
    },
    {
      path: '/dev/references',
      name: 'dev-references',
      component: () => import('@/views/developer/ReferenceDesigns.vue'),
      meta: { title: '参考设计库', requiresAuth: true },
    },
    {
      path: '/dev/test-kits',
      name: 'dev-test-kits',
      component: () => import('@/views/developer/TestKits.vue'),
      meta: { title: '测试治具', requiresAuth: true },
    },
    {
      path: '/dev/docs',
      name: 'dev-docs',
      component: () => import('@/views/developer/DevDocs.vue'),
      meta: { title: '开发文档' },
    },
    {
      path: '/dev/self-check',
      name: 'dev-self-check',
      component: () => import('@/views/developer/SelfCheck.vue'),
      meta: { title: '认证自查', requiresAuth: true },
    },
    // 管理后台
    {
      path: '/admin',
      name: 'admin-dashboard',
      component: () => import('@/views/admin/AdminDashboard.vue'),
      meta: { title: '运营仪表板', requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/applications',
      name: 'admin-applications',
      component: () => import('@/views/admin/ApplicationReview.vue'),
      meta: { title: '申请审核', requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/certificates',
      name: 'admin-certificates',
      component: () => import('@/views/admin/CertificateManager.vue'),
      meta: { title: '证书管理', requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/standards',
      name: 'admin-standards',
      component: () => import('@/views/admin/StandardManager.vue'),
      meta: { title: '标准管理', requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/laboratories',
      name: 'admin-labs',
      component: () => import('@/views/admin/LaboratoryManager.vue'),
      meta: { title: '实验室管理', requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/security',
      name: 'admin-security',
      component: () => import('@/views/admin/SecurityAudit.vue'),
      meta: { title: '安全审计', requiresAuth: true, requiresAdmin: true },
    },
    // 实验室门户
    {
      path: '/lab',
      name: 'lab-dashboard',
      component: () => import('@/views/lab/LabDashboard.vue'),
      meta: { title: '实验室仪表板', requiresAuth: true, requiresLab: true },
    },
    {
      path: '/lab/assignments',
      name: 'lab-assignments',
      component: () => import('@/views/lab/AssignmentList.vue'),
      meta: { title: '测试任务', requiresAuth: true, requiresLab: true },
    },
    {
      path: '/lab/assignments/:id',
      name: 'lab-assignment-detail',
      component: () => import('@/views/lab/AssignmentDetail.vue'),
      meta: { title: '任务详情', requiresAuth: true, requiresLab: true },
    },
    {
      path: '/lab/equipment',
      name: 'lab-equipment',
      component: () => import('@/views/lab/EquipmentManager.vue'),
      meta: { title: '设备管理', requiresAuth: true, requiresLab: true },
    },
  ],
})

router.beforeEach((to, _from, next) => {
  document.title = (to.meta.title as string) || 'MFQ 认证门户'
  next()
})

export default router
