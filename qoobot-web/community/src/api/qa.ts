import client from './client'

export interface Question {
  id: number
  userId: string
  title: string
  content: string
  contentHtml: string
  viewCount: number
  answerCount: number
  voteScore: number
  isSolved: boolean
  createdAt: string
}

export const qaApi = {
  getQuestions: (params?: { sort?: string; page?: number; size?: number }) =>
    client.get('/v1/qa/questions', { params }),
  getQuestion: (id: number) => client.get(`/v1/qa/questions/${id}`),
  createQuestion: (data: { title: string; content: string; contentHtml: string }) =>
    client.post('/v1/qa/questions', data),
  getAnswers: (questionId: number) => client.get(`/v1/qa/questions/${questionId}/answers`),
  createAnswer: (questionId: number, data: { content: string; contentHtml: string }) =>
    client.post(`/v1/qa/questions/${questionId}/answer`, data),
  vote: (type: string, id: number, voteType: string) =>
    client.post(`/v1/qa/${type}/${id}/vote`, { voteType }),
  acceptAnswer: (answerId: number) => client.post(`/v1/qa/answers/${answerId}/accept`)
}
