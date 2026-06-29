import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const userId = ref(localStorage.getItem('userId') || '')
  const nickname = ref('')
  const avatarUrl = ref('')
  const isLoggedIn = computed(() => !!userId.value)

  function login(id: string, name: string, avatar?: string) {
    userId.value = id
    nickname.value = name
    avatarUrl.value = avatar || ''
    localStorage.setItem('userId', id)
  }

  function logout() {
    userId.value = ''
    nickname.value = ''
    avatarUrl.value = ''
    localStorage.removeItem('userId')
  }

  return { userId, nickname, avatarUrl, isLoggedIn, login, logout }
})
