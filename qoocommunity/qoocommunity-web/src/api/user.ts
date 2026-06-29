import client from './client'

export interface UserProfile {
  userId: string
  nickname: string
  avatarUrl: string
  email: string
  bio: string
  registeredAt: string
}

export const userApi = {
  getProfile: () => client.get('/v1/users/me'),
  updateProfile: (data: Partial<UserProfile>) => client.put('/v1/users/me', data)
}
