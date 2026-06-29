import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type LoginRequest } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('qooauth_admin_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('qooauth_admin_refresh_token'))
  const user = ref<{ id: string; email: string; name: string; roles: string[] } | null>(
    JSON.parse(localStorage.getItem('qooauth_admin_user') || 'null')
  )
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.roles?.includes('ROLE_ADMIN') ?? false)

  async function login(credentials: LoginRequest) {
    loading.value = true
    error.value = null
    try {
      const response = await authApi.login(credentials)
      token.value = response.access_token
      refreshToken.value = response.refresh_token
      user.value = response.user

      localStorage.setItem('qooauth_admin_token', response.access_token)
      localStorage.setItem('qooauth_admin_refresh_token', response.refresh_token)
      localStorage.setItem('qooauth_admin_user', JSON.stringify(response.user))
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Login failed'
      error.value = msg
      throw e
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('qooauth_admin_token')
    localStorage.removeItem('qooauth_admin_refresh_token')
    localStorage.removeItem('qooauth_admin_user')
  }

  return {
    token,
    refreshToken,
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    login,
    logout,
  }
})
