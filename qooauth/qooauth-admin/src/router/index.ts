import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: 'Login', requiresAuth: false },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: 'Dashboard', requiresAuth: true },
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('@/views/UserManagement.vue'),
    meta: { title: 'User Management', requiresAuth: true },
  },
  {
    path: '/devices',
    name: 'DeviceManagement',
    component: () => import('@/views/DeviceManagement.vue'),
    meta: { title: 'Device Management', requiresAuth: true },
  },
  {
    path: '/oauth-clients',
    name: 'OAuthClients',
    component: () => import('@/views/OAuthClients.vue'),
    meta: { title: 'OAuth Clients', requiresAuth: true },
  },
  {
    path: '/api-keys',
    name: 'ApiKeys',
    component: () => import('@/views/ApiKeys.vue'),
    meta: { title: 'API Keys', requiresAuth: true },
  },
  {
    path: '/audit-logs',
    name: 'AuditLogs',
    component: () => import('@/views/AuditLogs.vue'),
    meta: { title: 'Audit Logs', requiresAuth: true },
  },
  {
    path: '/security-alerts',
    name: 'SecurityAlerts',
    component: () => import('@/views/SecurityAlerts.vue'),
    meta: { title: 'Security Alerts', requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: 'Settings', requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard for auth
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('qooauth_admin_token')
  if (to.meta.requiresAuth !== false && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
