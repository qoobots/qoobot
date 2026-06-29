import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'TeleopPanel',
    component: () => import('@/views/TeleopPanel.vue'),
    meta: { title: '远程遥控面板' }
  },
  {
    path: '/sessions',
    name: 'SessionList',
    component: () => import('@/views/SessionList.vue'),
    meta: { title: '会话列表' }
  },
  {
    path: '/teaching',
    name: 'TeachingRecords',
    component: () => import('@/views/TeachingRecords.vue'),
    meta: { title: '示教记录' }
  },
  {
    path: '/diagnostics',
    name: 'Diagnostics',
    component: () => import('@/views/Diagnostics.vue'),
    meta: { title: '远程诊断' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  document.title = (to.meta.title as string) || 'qooremote'
  next()
})

export default router
