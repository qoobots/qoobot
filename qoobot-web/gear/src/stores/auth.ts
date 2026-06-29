import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('qoogear_token') || '')
  const user = ref<any>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isLab = computed(() => user.value?.role === 'lab')
  const isDeveloper = computed(() => user.value?.role === 'developer')

  function login(newToken: string, userInfo: any) {
    token.value = newToken
    user.value = userInfo
    localStorage.setItem('qoogear_token', newToken)
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('qoogear_token')
  }

  return { token, user, isLoggedIn, isAdmin, isLab, isDeveloper, login, logout }
})
