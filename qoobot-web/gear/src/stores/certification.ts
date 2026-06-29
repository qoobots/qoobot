import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { CertificationApplication, Certificate } from '@/types/certification'

export const useCertificationStore = defineStore('certification', () => {
  const applications = ref<CertificationApplication[]>([])
  const certificates = ref<Certificate[]>([])
  const loading = ref(false)

  function setApplications(data: CertificationApplication[]) {
    applications.value = data
  }

  function addApplication(app: CertificationApplication) {
    applications.value.unshift(app)
  }

  function updateApplication(id: number, data: Partial<CertificationApplication>) {
    const idx = applications.value.findIndex((a) => a.id === id)
    if (idx >= 0) {
      applications.value[idx] = { ...applications.value[idx], ...data }
    }
  }

  function setCertificates(data: Certificate[]) {
    certificates.value = data
  }

  return {
    applications,
    certificates,
    loading,
    setApplications,
    addApplication,
    updateApplication,
    setCertificates,
  }
})
