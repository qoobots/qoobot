import client from './client'
import type { ApiResponse } from '@/types/certification'

const BASE = '/auth'

export interface LoginResponse {
  token: string
  refreshToken: string
  user: {
    id: number
    username: string
    roles: string[]
  }
}

export const authApi = {
  login: (username: string, password: string) =>
    client.post<ApiResponse<LoginResponse>>(`${BASE}/login`, { username, password }),

  refreshToken: (refreshToken: string) =>
    client.post<ApiResponse<{ token: string; refreshToken: string }>>(`${BASE}/refresh`, { refreshToken }),

  logout: () =>
    client.post<ApiResponse<null>>(`${BASE}/logout`),

  getCurrentUser: () =>
    client.get<ApiResponse<LoginResponse['user']>>(`${BASE}/me`),
}
