import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi, type AuthStats } from '@/api/auth'

export const useAdminStore = defineStore('admin', () => {
  const stats = ref<AuthStats>({
    totalUsers: 0,
    activeUsers: 0,
    totalDevices: 0,
    activeSessions: 0,
    apiKeysActive: 0,
    securityAlerts: 0,
  })
  const statsLoading = ref(false)

  async function fetchStats() {
    statsLoading.value = true
    try {
      const data = await authApi.getStats()
      stats.value = data
    } catch {
      // Use mock data if endpoint is not available
      stats.value = {
        totalUsers: 0,
        activeUsers: 0,
        totalDevices: 0,
        activeSessions: 0,
        apiKeysActive: 0,
        securityAlerts: 0,
      }
    } finally {
      statsLoading.value = false
    }
  }

  return {
    stats,
    statsLoading,
    fetchStats,
  }
})
