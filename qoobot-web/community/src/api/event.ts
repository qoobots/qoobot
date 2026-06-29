import client from './client'

export interface Event {
  id: number
  title: string
  slug: string
  type: string
  description: string
  coverUrl: string
  location: string
  startTime: string
  endTime: string
  maxAttendees: number
  currentAttendees: number
  status: string
  isFeatured: boolean
}

export const eventApi = {
  getEvents: (params?: { type?: string; status?: string }) => client.get('/v1/events', { params }),
  getEvent: (id: number) => client.get(`/v1/events/${id}`),
  register: (eventId: number, data: { name?: string; company?: string; title?: string; email?: string }) =>
    client.post(`/v1/events/${eventId}/register`, data),
  cancelRegistration: (eventId: number) => client.delete(`/v1/events/${eventId}/register`),
  getAttendees: (eventId: number) => client.get(`/v1/events/${eventId}/attendees`),
  getMaterials: (eventId: number) => client.get(`/v1/events/${eventId}/materials`),
  getCalendar: () => client.get('/v1/events/calendar')
}
