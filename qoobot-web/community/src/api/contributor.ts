import client from './client'

export interface Contributor {
  id: string
  userId: string
  nickname: string
  avatarUrl: string
  level: string
  bio: string
  contributeCount: number
  prCount: number
  issueCount: number
  claSigned: boolean
  joinedAt: string
}

export interface ContributorLevel {
  name: string
  icon: string
  minContributions: number
  color: string
}

export interface ContributorStats {
  userId: string
  prCount: number
  issueCount: number
  commitCount: number
  reviewCount: number
  totalContributions: number
  joinedAt: string
}

export const contributorApi = {
  getContributors: () => client.get('/v1/contributors'),
  getContributor: (userId: string) => client.get(`/v1/contributors/${userId}`),
  signCla: (claType: string) => client.post('/v1/contributors/cla', { claType }),
  getClaStatus: () => client.get('/v1/contributors/cla/status'),
  getLevels: () => client.get('/v1/contributors/levels'),
  getGoodFirstIssues: () => client.get('/v1/contributors/good-first-issues'),
  getContributorStats: (userId: string) => client.get(`/v1/contributors/${userId}/stats`),
  getContributorWall: () => client.get('/v1/contributors/wall')
}
