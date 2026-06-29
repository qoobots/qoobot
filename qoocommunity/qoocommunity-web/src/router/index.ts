import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: 'QooBot Community' }
  },
  // 论坛
  {
    path: '/forums',
    name: 'ForumIndex',
    component: () => import('@/views/forum/ForumIndex.vue'),
    meta: { title: '技术论坛' }
  },
  {
    path: '/forums/c/:category',
    name: 'ForumCategory',
    component: () => import('@/views/forum/ForumCategory.vue'),
    meta: { title: '论坛分类' }
  },
  {
    path: '/forums/t/:id',
    name: 'TopicView',
    component: () => import('@/views/forum/TopicView.vue'),
    meta: { title: '帖子详情' }
  },
  // Q&A
  {
    path: '/qa',
    name: 'QaIndex',
    component: () => import('@/views/qa/QaIndex.vue'),
    meta: { title: '问答社区' }
  },
  {
    path: '/qa/q/:id',
    name: 'QuestionView',
    component: () => import('@/views/qa/QuestionView.vue'),
    meta: { title: '问题详情' }
  },
  // 活动
  {
    path: '/events',
    name: 'EventIndex',
    component: () => import('@/views/events/EventIndex.vue'),
    meta: { title: '活动中心' }
  },
  {
    path: '/events/:id',
    name: 'EventDetail',
    component: () => import('@/views/events/EventDetail.vue'),
    meta: { title: '活动详情' }
  },
  // 学院
  {
    path: '/academy',
    name: 'AcademyIndex',
    component: () => import('@/views/academy/AcademyIndex.vue'),
    meta: { title: 'QooBot Academy' }
  },
  {
    path: '/academy/courses/:id',
    name: 'CourseView',
    component: () => import('@/views/academy/CourseView.vue'),
    meta: { title: '课程详情' }
  },
  {
    path: '/academy/courses/:courseId/lessons/:lessonId',
    name: 'LessonView',
    component: () => import('@/views/academy/LessonView.vue'),
    meta: { title: '课时学习' }
  },
  {
    path: '/academy/learning-paths',
    name: 'LearningPathIndex',
    component: () => import('@/views/academy/LearningPathIndex.vue'),
    meta: { title: '学习路径' }
  },
  {
    path: '/academy/learning-paths/:slug',
    name: 'LearningPathDetail',
    component: () => import('@/views/academy/LearningPathDetail.vue'),
    meta: { title: '学习路径详情' }
  },
  {
    path: '/academy/cert',
    name: 'CertCenter',
    component: () => import('@/views/academy/CertCenter.vue'),
    meta: { title: '认证中心' }
  },
  {
    path: '/academy/cert/:id',
    name: 'CertDetail',
    component: () => import('@/views/academy/CertDetail.vue'),
    meta: { title: '认证详情' }
  },
  {
    path: '/academy/learning-paths',
    name: 'LearningPathIndex',
    component: () => import('@/views/academy/LearningPathIndex.vue'),
    meta: { title: '学习路径' }
  },
  {
    path: '/academy/learning-paths/:slug',
    name: 'LearningPathDetail',
    component: () => import('@/views/academy/LearningPathDetail.vue'),
    meta: { title: '学习路径详情' }
  },
  {
    path: '/academy/courses/:courseId/lessons/:lessonId',
    name: 'LessonView',
    component: () => import('@/views/academy/LessonView.vue'),
    meta: { title: '课时学习' }
  },
  // 贡献者
  {
    path: '/contributors',
    name: 'ContributorWall',
    component: () => import('@/views/contributors/ContributorWall.vue'),
    meta: { title: '贡献者墙' }
  },
  {
    path: '/contributors/cla',
    name: 'ClaSign',
    component: () => import('@/views/contributors/ClaSignView.vue'),
    meta: { title: 'CLA 签署' }
  },
  {
    path: '/contributors/levels',
    name: 'LevelGuide',
    component: () => import('@/views/contributors/LevelGuide.vue'),
    meta: { title: '贡献者等级' }
  },
  {
    path: '/contributors/:id',
    name: 'ContributorProfile',
    component: () => import('@/views/contributors/ContributorProfile.vue'),
    meta: { title: '贡献者主页' }
  },
  // 治理
  {
    path: '/governance',
    name: 'Governance',
    redirect: '/governance/charter'
  },
  {
    path: '/governance/charter',
    name: 'CharterView',
    component: () => import('@/views/governance/CharterView.vue'),
    meta: { title: '社区宪章' }
  },
  {
    path: '/governance/rfcs',
    name: 'RfcList',
    component: () => import('@/views/governance/RfcList.vue'),
    meta: { title: 'RFC 提案' }
  },
  {
    path: '/governance/rfcs/:id',
    name: 'RfcDetail',
    component: () => import('@/views/governance/RfcDetail.vue'),
    meta: { title: 'RFC 详情' }
  },
  {
    path: '/governance/roadmap',
    name: 'RoadmapView',
    component: () => import('@/views/governance/RoadmapView.vue'),
    meta: { title: '路线图' }
  },
  {
    path: '/governance/tsc-sig',
    name: 'TscSig',
    component: () => import('../views/governance/TscSigView.vue'),
    meta: { title: '治理结构' }
  },
  // 内容
  {
    path: '/blog',
    name: 'BlogIndex',
    component: () => import('@/views/content/BlogIndex.vue'),
    meta: { title: '技术博客' }
  },
  {
    path: '/blog/:slug',
    name: 'BlogDetail',
    component: () => import('@/views/content/BlogDetail.vue'),
    meta: { title: '博客详情' }
  },
  {
    path: '/showcase',
    name: 'ShowcaseIndex',
    component: () => import('@/views/content/ShowcaseIndex.vue'),
    meta: { title: '案例展示' }
  },
  {
    path: '/showcase/:id',
    name: 'ShowcaseDetail',
    component: () => import('@/views/content/ShowcaseDetail.vue'),
    meta: { title: '案例详情' }
  },
  // 仪表盘
  {
    path: '/dashboard',
    name: 'Dashboard',
    redirect: '/dashboard/profile'
  },
  {
    path: '/dashboard/profile',
    name: 'ProfileView',
    component: () => import('@/views/dashboard/ProfileView.vue'),
    meta: { title: '个人资料' }
  },
  {
    path: '/dashboard/courses',
    name: 'MyCoursesView',
    component: () => import('@/views/dashboard/MyCoursesView.vue'),
    meta: { title: '我的课程' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach((to) => {
  document.title = (to.meta.title as string) || 'QooBot Community'
})

export default router
