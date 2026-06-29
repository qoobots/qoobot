import apiClient from './auth'

export interface User {
  userId: string
  email: string
  displayName: string
  avatarUrl: string
  roles: string[]
  state: string
  createdAt: string
  updatedAt: string
  lastLoginAt: string | null
}

export interface UserListParams {
  page?: number
  pageSize?: number
  state?: string
  search?: string
  sortBy?: string
  sortDirection?: string
}

export interface UserListResponse {
  users: User[]
  totalCount: number
  page: number
  pageSize: number
}

export interface UpdateUserRequest {
  displayName?: string
  roles?: string[]
  state?: string
}

export const userApi = {
  list(params: UserListParams = {}): Promise<UserListResponse> {
    return apiClient.get('/users', { params }).then((r) => r.data)
  },

  get(userId: string): Promise<User> {
    return apiClient.get(`/users/${userId}`).then((r) => r.data)
  },

  update(userId: string, data: UpdateUserRequest): Promise<User> {
    return apiClient.put(`/users/${userId}`, data).then((r) => r.data)
  },

  delete(userId: string): Promise<void> {
    return apiClient.delete(`/users/${userId}`)
  },

  freeze(userId: string): Promise<User> {
    return apiClient.post(`/users/${userId}/freeze`).then((r) => r.data)
  },

  unfreeze(userId: string): Promise<User> {
    return apiClient.post(`/users/${userId}/unfreeze`).then((r) => r.data)
  },

  search(query: string, params: UserListParams = {}): Promise<UserListResponse> {
    return apiClient.get('/users/search', { params: { q: query, ...params } }).then((r) => r.data)
  },
}
