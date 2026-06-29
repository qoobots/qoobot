import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('qooauth_admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('qooauth_admin_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token: string
  user: {
    id: string
    email: string
    name: string
    roles: string[]
  }
}

export interface AuthStats {
  totalUsers: number
  activeUsers: number
  totalDevices: number
  activeSessions: number
  apiKeysActive: number
  securityAlerts: number
}

export const authApi = {
  login(data: LoginRequest): Promise<LoginResponse> {
    return apiClient.post('/auth/login', data).then((r) => r.data)
  },

  logout(): Promise<void> {
    return apiClient.post('/auth/logout')
  },

  refreshToken(refreshToken: string): Promise<LoginResponse> {
    return apiClient.post('/auth/token', { grant_type: 'refresh_token', refresh_token: refreshToken }).then((r) => r.data)
  },

  getStats(): Promise<AuthStats> {
    return apiClient.get('/auth/stats').then((r) => r.data)
  },
}

export default apiClient
