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

  reviewApplication: (id: number, approved: boolean, comment: string) =>
    client.post<ApiResponse<CertificationApplication>>(`${BASE}/applications/${id}/review`, { approved, comment }),

  assignLab: (id: number, labId: number) =>
    client.post<ApiResponse<CertificationApplication>>(`${BASE}/applications/${id}/assign-lab`, { labId }),

  // 证书
  listCertificates: (params?: Record<string, any>) =>
    client.get<ApiResponse<PageResponse<Certificate>>>(`${BASE}/certificates`, { params }),

  getCertificate: (id: number) =>
    client.get<ApiResponse<Certificate>>(`${BASE}/certificates/${id}`),

  verifyCertificate: (id: number) =>
    client.get<ApiResponse<Certificate>>(`${BASE}/certificates/${id}/verify`),
}
