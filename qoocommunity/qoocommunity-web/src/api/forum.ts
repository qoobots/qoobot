import client from './client'

export interface Topic {
  id: number
  categoryId: number
  userId: string
  title: string
  content: string
  contentHtml: string
  isPinned: boolean
  isLocked: boolean
  viewCount: number
  replyCount: number
  likeCount: number
  createdAt: string
  updatedAt: string
  lastReplyAt: string
}

export interface Category {
  id: number
  name: string
  slug: string
  description: string
  sortOrder: number
  topicCount: number
}

export const forumApi = {
  getCategories: () => client.get<Category[]>('/v1/forums/categories'),
  getCategory: (slug: string) => client.get<Category>(`/v1/forums/categories/${slug}`),
  getTopics: (params?: { categoryId?: number; sort?: string; page?: number; size?: number }) =>
    client.get('/v1/forums/topics', { params }),
  getTopic: (id: number) => client.get<Topic>(`/v1/forums/topics/${id}`),
  createTopic: (data: { categoryId: number; title: string; content: string; contentHtml: string }) =>
    client.post<Topic>('/v1/forums/topics', data),
  getReplies: (topicId: number) => client.get(`/v1/forums/topics/${topicId}/replies`),
  createReply: (topicId: number, data: { parentId?: number; content: string; contentHtml: string }) =>
    client.post(`/v1/forums/topics/${topicId}/reply`, data),
  toggleLike: (type: string, targetId: number) => client.post(`/v1/forums/${type}/${targetId}/like`),
  toggleBookmark: (topicId: number) => client.post(`/v1/forums/topics/${topicId}/bookmark`),
  search: (q: string, page = 0, size = 20) => client.get('/v1/forums/search', { params: { q, page, size } })
}
