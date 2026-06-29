import client from './client'
import type { StandardSpec, StandardCategory, ApiResponse, PageResponse } from '@/types/certification'

const BASE = '/standard'

export const standardApi = {
  listCategories: () =>
    client.get<ApiResponse<StandardCategory[]>>(`${BASE}/categories`),

  getCategory: (id: number) =>
    client.get<ApiResponse<StandardCategory>>(`${BASE}/categories/${id}`),

  listSpecs: (params?: Record<string, any>) =>
    client.get<ApiResponse<PageResponse<StandardSpec>>>(`${BASE}/specs`, { params }),

  getSpec: (id: number) =>
    client.get<ApiResponse<StandardSpec>>(`${BASE}/specs/${id}`),

  getSpecVersions: (id: number) =>
    client.get<ApiResponse<StandardSpec[]>>(`${BASE}/specs/${id}/versions`),

  createSpec: (data: Partial<StandardSpec>) =>
    client.post<ApiResponse<StandardSpec>>(`${BASE}/specs`, data),

  updateSpec: (id: number, data: Partial<StandardSpec>) =>
    client.put<ApiResponse<StandardSpec>>(`${BASE}/specs/${id}`, data),

  publishSpec: (id: number) =>
    client.post<ApiResponse<StandardSpec>>(`${BASE}/specs/${id}/publish`),

  deprecateSpec: (id: number) =>
    client.post<ApiResponse<StandardSpec>>(`${BASE}/specs/${id}/deprecate`),
}
