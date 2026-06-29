import client from './client'
import type {
  ApiResponse,
  TeleopSession,
  TeachingRecord,
  DiagnosticEvent
} from '@/types/teleop'

// ========== 会话管理 ==========

export const sessionApi = {
  list: () =>
    client.get<ApiResponse<TeleopSession[]>>('/sessions'),

  create: (data: { robot_id: string; operator_id: string; media_types: string[] }) =>
    client.post<ApiResponse<TeleopSession>>('/sessions', data),

  get: (id: string) =>
    client.get<ApiResponse<TeleopSession>>(`/sessions/${id}`),

  terminate: (id: string) =>
    client.delete<ApiResponse<null>>(`/sessions/${id}`),

  takeover: (id: string) =>
    client.post<ApiResponse<null>>(`/sessions/${id}/takeover`),

  release: (id: string) =>
    client.post<ApiResponse<null>>(`/sessions/${id}/release`),

  heartbeat: (id: string) =>
    client.post<ApiResponse<null>>(`/sessions/${id}/heartbeat`)
}

// ========== 示教录制 ==========

export const teachingApi = {
  list: (params?: { robot_id?: string; operator_id?: string; keyword?: string }) =>
    client.get<ApiResponse<TeachingRecord[]>>('/recordings', { params }),

  get: (id: string) =>
    client.get<ApiResponse<TeachingRecord>>(`/recordings/${id}`),

  start: (id: string) =>
    client.post<ApiResponse<null>>(`/recordings/${id}/start`),

  stop: (id: string) =>
    client.post<ApiResponse<null>>(`/recordings/${id}/stop`),

  download: (id: string) =>
    client.get(`/recordings/${id}/download`, { responseType: 'blob' }),

  verify: (id: string, verified: boolean) =>
    client.post<ApiResponse<null>>(`/recordings/${id}/verify`, { is_verified: verified })
}

// ========== 机器人 ==========

export const robotApi = {
  list: () =>
    client.get<ApiResponse<any[]>>('/robots'),

  status: (id: string) =>
    client.get<ApiResponse<any>>(`/robots/${id}/status`),

  streams: (id: string) =>
    client.get<ApiResponse<any[]>>(`/robots/${id}/streams`)
}

// ========== 诊断 ==========

export const diagnosticsApi = {
  events: (params?: { session_id?: string; severity?: string; limit?: number }) =>
    client.get<ApiResponse<DiagnosticEvent[]>>('/diagnostics/events', { params })
}
