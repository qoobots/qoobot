import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor - attach auth token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle errors
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: (data: { email: string; password: string }) =>
    apiClient.post('/auth/login', data),
  logout: () => apiClient.post('/auth/logout'),
  mfaVerify: (data: { mfaToken: string; code: string }) =>
    apiClient.post('/auth/mfa/verify', data),
};

// Users API
export const usersApi = {
  list: (params?: { page?: number; pageSize?: number; search?: string }) =>
    apiClient.get('/users', { params }),
  getById: (userId: string) => apiClient.get(`/users/${userId}`),
  freeze: (userId: string) => apiClient.post(`/users/${userId}/freeze`),
  unfreeze: (userId: string) => apiClient.post(`/users/${userId}/unfreeze`),
  delete: (userId: string) => apiClient.delete(`/users/${userId}`),
};

// Devices API
export const devicesApi = {
  list: (params?: { page?: number; pageSize?: number; userId?: string }) =>
    apiClient.get('/devices', { params }),
  getById: (deviceId: string) => apiClient.get(`/devices/${deviceId}`),
  lock: (deviceId: string) => apiClient.post(`/devices/${deviceId}/lock`),
  unlock: (deviceId: string) => apiClient.post(`/devices/${deviceId}/unlock`),
  wipe: (deviceId: string) => apiClient.post(`/devices/${deviceId}/wipe`),
};

// OAuth Clients API
export const oauthApi = {
  list: (params?: { page?: number; pageSize?: number }) =>
    apiClient.get('/developer/apps', { params }),
  approve: (clientId: string) =>
    apiClient.post(`/developer/apps/${clientId}/approve`),
  revoke: (clientId: string) =>
    apiClient.post(`/developer/apps/${clientId}/revoke`),
  delete: (clientId: string) =>
    apiClient.delete(`/developer/apps/${clientId}`),
};

// API Keys API
export const apiKeysApi = {
  list: (params?: { page?: number; pageSize?: number }) =>
    apiClient.get('/api-keys', { params }),
  revoke: (keyId: string) => apiClient.delete(`/api-keys/${keyId}`),
};

// Audit Logs API
export const auditApi = {
  list: (params?: {
    page?: number;
    pageSize?: number;
    startTime?: string;
    endTime?: string;
    action?: string;
    actorId?: string;
  }) => apiClient.get('/audit/logs', { params }),
  export: (params: { startTime: string; endTime: string; format?: string }) =>
    apiClient.get('/audit/logs/export', { params, responseType: 'blob' }),
};

// Security Alerts API
export const securityApi = {
  list: (params?: { page?: number; pageSize?: number; severity?: string }) =>
    apiClient.get('/security/events', { params }),
  resolve: (eventId: string) =>
    apiClient.post(`/security/events/${eventId}/resolve`),
  getStats: () => apiClient.get('/security/stats'),
};

// Dashboard API
export const dashboardApi = {
  getStats: () => apiClient.get('/admin/dashboard/stats'),
};

export default apiClient;
