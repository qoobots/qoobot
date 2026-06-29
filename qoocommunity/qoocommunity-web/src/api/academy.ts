import client from './client'

export interface Course {
  id: number
  title: string
  slug: string
  description: string
  coverUrl: string
  level: string
  category: string
  lessonCount: number
  enrolledCount: number
  durationMinutes: number
}

export interface LearningPath {
  id: number
  title: string
  slug: string
  description: string
  coverUrl: string
  level: string
  courseCount: number
  sortOrder: number
  isPublished: boolean
  createdAt: string
}

export interface Lesson {
  id: number
  courseId: number
  title: string
  description: string
  content: string
  contentHtml: string
  videoUrl: string
  duration: number
  sortOrder: number
  isPublished: boolean
  createdAt: string
}

export interface LessonProgress {
  id: number
  userId: string
  lessonId: number
  isCompleted: boolean
  completedAt: string
}

export interface Certification {
  id: number
  name: string
  slug: string
  level: string
  description: string
  examDuration: number
  passScore: number
  questionCount: number
}

export const academyApi = {
  getCourses: (params?: { level?: string; category?: string }) => client.get('/v1/academy/courses', { params }),
  getCourse: (id: number) => client.get(`/v1/academy/courses/${id}`),
  enroll: (courseId: number) => client.post(`/v1/academy/courses/${courseId}/enroll`),
  updateProgress: (courseId: number, data: { lessonId: number; progressPct: number; isCompleted: boolean }) =>
    client.put(`/v1/academy/progress/${courseId}`, data),
  getMyCourses: () => client.get('/v1/academy/my-courses'),
  getCertifications: () => client.get('/v1/academy/certifications'),
  getCertification: (id: number) => client.get(`/v1/academy/certifications/${id}`),
  submitExam: (certId: number, answers: any) => client.post(`/v1/academy/certifications/${certId}/exam`, { answers }),
  getMyCerts: () => client.get('/v1/academy/certifications/my'),
  getLearningPaths: () => client.get('/v1/academy/learning-paths'),
  getLearningPath: (slug: string) => client.get(`/v1/academy/learning-paths/${slug}`),
  getLessons: (courseId: number) => client.get(`/v1/academy/courses/${courseId}/lessons`),
  getLesson: (courseId: number, lessonId: number) => client.get(`/v1/academy/courses/${courseId}/lessons/${lessonId}`),
  markLessonComplete: (lessonId: number) => client.post(`/v1/academy/lessons/${lessonId}/complete`),
  markLessonIncomplete: (lessonId: number) => client.delete(`/v1/academy/lessons/${lessonId}/complete`),
  getMyProgress: () => client.get('/v1/academy/my-progress')
}
