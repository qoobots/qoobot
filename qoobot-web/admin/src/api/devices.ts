import apiClient from './auth'

export interface Device {
  deviceId: string
  userId: string
  deviceName: string
  deviceType: string
  serialNumber: string
  state: string
  certificateSha256: string | null
  registeredAt: string
  lastSeenAt: string | null
  certificateExpiresAt: string | null
}

export interface DeviceListParams {
  page?: number
  pageSize?: number
  state?: string
  deviceType?: string
  search?: string
}

export interface DeviceListResponse {
  devices: Device[]
  totalCount: number
  page: number
  pageSize: number
}

export const deviceApi = {
  list(params: DeviceListParams = {}): Promise<DeviceListResponse> {
    return apiClient.get('/devices', { params }).then((r) => r.data)
  },

  get(deviceId: string): Promise<Device> {
    return apiClient.get(`/devices/${deviceId}`).then((r) => r.data)
  },

  lock(deviceId: string): Promise<Device> {
    return apiClient.post(`/devices/${deviceId}/lock`).then((r) => r.data)
  },

  unlock(deviceId: string): Promise<Device> {
    return apiClient.post(`/devices/${deviceId}/unlock`).then((r) => r.data)
  },

  wipe(deviceId: string): Promise<void> {
    return apiClient.post(`/devices/${deviceId}/wipe`)
  },

  revoke(deviceId: string): Promise<void> {
    return apiClient.delete(`/devices/${deviceId}`)
  },
}
