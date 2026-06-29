import client from './client'
import type { ReferenceDesign, SdkRelease, TestKit, ApiResponse, PageResponse } from '@/types/certification'

const BASE = '/developer'

export const developerApi = {
  getDashboard: () =>
    client.get<ApiResponse<any>>(`${BASE}/dashboard`),

  listSdk: () =>
    client.get<ApiResponse<SdkRelease[]>>(`${BASE}/sdk`),

  getLatestSdk: (platform: string) =>
    client.get(`${BASE}/sdk/${platform}/latest`, { responseType: 'blob' }),

  listReferences: (params?: Record<string, any>) =>
    client.get<ApiResponse<PageResponse<ReferenceDesign>>>(`${BASE}/references`, { params }),

  getReference: (id: number) =>
    client.get<ApiResponse<ReferenceDesign>>(`${BASE}/references/${id}`),

  downloadReference: (id: number) =>
    client.get(`${BASE}/references/${id}/download`, { responseType: 'blob' }),

  listTestKits: () =>
    client.get<ApiResponse<TestKit[]>>(`${BASE}/test-kits`),

  orderTestKit: (kitId: number) =>
    client.post<ApiResponse<any>>(`${BASE}/test-kits/order`, { kitId }),

  getDocs: () =>
    client.get<ApiResponse<any>>(`${BASE}/docs`),

  getDoc: (slug: string) =>
    client.get<ApiResponse<any>>(`${BASE}/docs/${slug}`),
}
