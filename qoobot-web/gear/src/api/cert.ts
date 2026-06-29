import client from './client'
import type {
  CertificationApplication,
  Certificate,
  ApiResponse,
  PageResponse,
} from '@/types/certification'

const BASE = '/cert'

export const certApi = {
  // 认证申请
  createApplication: (data: Partial<CertificationApplication>) =>
    client.post<ApiResponse<CertificationApplication>>(`${BASE}/applications`, data),

  listApplications: (params?: Record<string, any>) =>
    client.get<ApiResponse<PageResponse<CertificationApplication>>>(`${BASE}/applications`, { params }),

  getApplication: (id: number) =>
    client.get<ApiResponse<CertificationApplication>>(`${BASE}/applications/${id}`),

  updateApplication: (id: number, data: Partial<CertificationApplication>) =>
    client.put<ApiResponse<CertificationApplication>>(`${BASE}/applications/${id}`, data),

  submitApplication: (id: number) =>
    client.post<ApiResponse<CertificationApplication>>(`${BASE}/applications/${id}/submit`),

  reviewApplication: (id: number, data: { reviewerId?: number; approved: boolean; comment?: string }) =>
    client.post<ApiResponse<CertificationApplication>>(`${BASE}/applications/${id}/review`, data),

  assignLab: (id: number, labId: number) =>
    client.post<ApiResponse<CertificationApplication>>(`${BASE}/applications/${id}/assign-lab`, { labId }),

  requestInfo: (id: number, message: string) =>
    client.post<ApiResponse<null>>(`${BASE}/applications/${id}/request-info`, { message }),

  // 证书
  listCertificates: (params?: Record<string, any>) =>
    client.get<ApiResponse<PageResponse<Certificate>>>(`${BASE}/certificates`, { params }),

  getCertificate: (id: number) =>
    client.get<ApiResponse<Certificate>>(`${BASE}/certificates/${id}`),

  verifyCertificate: (id: number) =>
    client.get<ApiResponse<Certificate>>(`${BASE}/certificates/${id}/verify`),

  revokeCertificate: (id: number, reason: string) =>
    client.post<ApiResponse<Certificate>>(`${BASE}/certificates/${id}/revoke`, { reason }),

  renewCertificate: (id: number, years: number) =>
    client.post<ApiResponse<Certificate>>(`${BASE}/certificates/${id}/renew`, { years }),

  // 实验室
  listLabs: () =>
    client.get<ApiResponse<{ id: number; name: string }[]>>('/lab/laboratories'),
}
