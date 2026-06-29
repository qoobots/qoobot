import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：添加用户认证头
client.interceptors.request.use((config) => {
  const userId = getUserId()
  if (userId) {
    config.headers['X-User-Id'] = userId
  }
  return config
})

// 响应拦截器：统一错误处理
client.interceptors.response.use(
  (response: AxiosResponse) => {
    const { code, message, data } = response.data
    if (code === 200) {
      return data
    }
    ElMessage.error(message || '请求失败')
    return Promise.reject(new Error(message))
  },
  (error) => {
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

function getUserId(): string | null {
  return localStorage.getItem('userId')
}

export function setUserId(id: string) {
  localStorage.setItem('userId', id)
}

export default client
