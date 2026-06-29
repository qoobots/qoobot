/** MFQ 认证申请 */
export interface CertificationApplication {
  id: number
  applicationId: string
  developerId: number
  developerName: string
  companyName: string
  productName: string
  productModel: string
  productCategory: ProductCategory
  certLevel: MfqLevel
  status: ApplicationStatus
  standardIds: string[]
  submittedAt: string
  reviewedBy: string
  reviewComment: string
  assignedLabId: number
  createdAt: string
  updatedAt: string
}

export type ProductCategory = 'gripper' | 'sensor_module' | 'wearable' | 'power' | 'mobility' | 'tool'

export type MfqLevel = 'basic' | 'premium' | 'pro'

export type ApplicationStatus =
  | 'draft' | 'submitted' | 'under_review' | 'lab_assigned'
  | 'lab_testing' | 'lab_passed' | 'lab_failed'
  | 'security_review' | 'approved' | 'rejected'
  | 'certificate_issued' | 'revoked' | 'expired'

/** MFQ 证书 */
export interface Certificate {
  id: number
  certificateId: string
  certNumber: string
  applicationId: string
  productName: string
  vendorName: string
  certLevel: MfqLevel
  issuedAt: string
  expiresAt: string
  revokedAt: string | null
  status: 'active' | 'expired' | 'revoked'
}

/** 接口标准 */
export interface StandardSpec {
  id: number
  specId: string
  specNumber: string
  categoryId: number
  categoryName: string
  title: string
  description: string
  version: string
  status: 'draft' | 'review' | 'published' | 'deprecated' | 'superseded'
  appliesTo: string[]
  publishedAt: string
  changelog: string
}

export interface StandardCategory {
  id: number
  categoryId: string
  name: string
  slug: string
  description: string
  icon: string
  parentId: number | null
  children: StandardCategory[]
}

/** 参考设计 */
export interface ReferenceDesign {
  id: number
  title: string
  category: string
  description: string
  files: string[]
  downloadCount: number
  publishedAt: string
}

/** SDK 发布 */
export interface SdkRelease {
  id: number
  platform: 'python' | 'cpp' | 'both'
  version: string
  downloadUrl: string
  releaseNotes: string
  releasedAt: string
  isLatest: boolean
}

/** 测试治具 */
export interface TestKit {
  id: number
  name: string
  description: string
  price: number
  stock: number
  compatible: string[]
}

/** 实验室 */
export interface Laboratory {
  id: number
  name: string
  address: string
  contact: string
  accredited: boolean
  scope: string[]
}

/** 安全审计 */
export interface SecurityAudit {
  id: number
  applicationId: string
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  auditor: string
  findings: Finding[]
  conclusion: string
  createdAt: string
}

export interface Finding {
  findingId: string
  description: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  recommendation: string
  status: 'open' | 'mitigated' | 'accepted' | 'closed'
}

/** API 通用响应 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface PageResponse<T> {
  content: T[]
  totalElements: number
  totalPages: number
  page: number
  size: number
}

/** 状态标签映射 */
export const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  submitted: '已提交',
  under_review: '审核中',
  lab_assigned: '已分配实验室',
  lab_testing: '实验室测试中',
  lab_passed: '测试通过',
  lab_failed: '测试未通过',
  security_review: '安全审查中',
  approved: '已批准',
  rejected: '已驳回',
  certificate_issued: '已颁发',
  revoked: '已吊销',
  expired: '已过期',
  active: '有效',
}

export const STATUS_COLORS: Record<string, string> = {
  draft: 'info',
  submitted: 'warning',
  under_review: 'warning',
  lab_assigned: 'warning',
  lab_testing: 'warning',
  lab_passed: 'success',
  lab_failed: 'danger',
  security_review: 'warning',
  approved: 'success',
  rejected: 'danger',
  certificate_issued: 'success',
  revoked: 'danger',
  expired: 'info',
  active: 'success',
}

export const CERT_LEVEL_LABELS: Record<string, string> = {
  basic: 'MFQ Basic',
  premium: 'MFQ Premium',
  pro: 'MFQ Pro',
}
