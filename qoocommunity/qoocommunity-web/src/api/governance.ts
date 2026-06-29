import client from './client'

export interface Charter {
  title: string
  content: string
  version: string
  adoptedAt: string
  updatedAt: string
}

export interface Rfc {
  id: number
  title: string
  slug: string
  status: string
  summary: string
  author: string
  createdAt: string
  updatedAt: string
  commentCount: number
}

export interface RoadmapItem {
  version: string
  title: string
  description: string
  status: string
  features: string[]
  targetDate: string
}

export interface TscMember {
  id: number
  userId: string
  nickname: string
  avatarUrl: string
  role: string
  joinedAt: string
}

export interface Sig {
  id: number
  name: string
  slug: string
  description: string
  leads: string[]
  memberCount: number
}

export const governanceApi = {
  getCharter: () => client.get('/v1/governance/charter'),
  getTscMembers: () => client.get('/v1/governance/tsc'),
  getSigs: () => client.get('/v1/governance/sigs'),
  getRfcs: () => client.get('/v1/governance/rfcs'),
  getRfc: (id: number) => client.get(`/v1/governance/rfcs/${id}`),
  getRoadmap: () => client.get('/v1/governance/roadmap'),
  getReports: () => client.get('/v1/governance/reports')
}
