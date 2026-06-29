import client from './client'

export interface Blog {
  id: number
  title: string
  slug: string
  summary: string
  content: string
  coverUrl: string
  author: string
  publishedAt: string
  createdAt: string
  viewCount: number
  tags: string[]
}

export interface Showcase {
  id: number
  title: string
  slug: string
  description: string
  coverUrl: string
  category: string
  author: string
  url: string
  createdAt: string
}

export const contentApi = {
  getBlogs: (params?: { page?: number; size?: number }) => client.get('/v1/content/blog', { params }),
  getBlog: (slug: string) => client.get(`/v1/content/blog/${slug}`),
  getShowcases: (params?: { category?: string; page?: number; size?: number }) =>
    client.get('/v1/content/showcase', { params }),
  getShowcase: (id: number) => client.get(`/v1/content/showcase/${id}`),
  submitShowcase: (data: any) => client.post('/v1/content/showcase', data),
  getBrandAssets: () => client.get('/v1/content/brand')
}
