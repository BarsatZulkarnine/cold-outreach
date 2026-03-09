import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export default api

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Target {
  id: number
  source: string
  company_name: string
  company_website?: string
  company_size?: string
  tech_stack: string[]
  contact_name?: string
  contact_title?: string
  contact_email?: string
  linkedin_url?: string
  has_open_roles: boolean
  open_role_url?: string
  notes?: string
  status: string
  created_at: string
  updated_at: string
  messages?: Message[]
}

export interface Message {
  id: number
  target_id: number
  channel: 'email' | 'linkedin'
  subject?: string
  body: string
  status: string
  generated_at: string
  sent_at?: string
  scheduled_send_at?: string
  opened: boolean
  replied: boolean
  follow_up_sent: boolean
}

export interface Stats {
  total_discovered: number
  emails_sent: number
  linkedin_sent: number
  replied: number
  meetings: number
  reply_rate: number
  by_status: Record<string, number>
}

export interface Persona {
  full_name: string
  short_name: string
  phone: string
  industry: string
  background: string
  tone_rules: string
}

// ─── API calls ───────────────────────────────────────────────────────────────

export const fetchTargets = (params?: Record<string, string | number | boolean>) =>
  api.get('/targets', { params }).then((r) => r.data)

export const fetchTarget = (id: number) =>
  api.get(`/targets/${id}`).then((r) => r.data)

export const fetchStats = () =>
  api.get('/targets/stats').then((r) => r.data as Stats)

export const updateTarget = (id: number, data: Partial<Target>) =>
  api.patch(`/targets/${id}`, data).then((r) => r.data)

export const discoverMaps = (queries?: string[], maxPerQuery = 20) =>
  api.post('/discover/maps', { queries, max_per_query: maxPerQuery }).then((r) => r.data)

export const discoverLinkedIn = (search_query: string, max_results = 15) =>
  api.post('/discover/linkedin', { search_query, max_results }).then((r) => r.data)

export const enrichTarget = (id: number) =>
  api.post(`/discover/enrich/${id}`).then((r) => r.data)

export const generateMessage = (targetId: number, channel: 'email' | 'linkedin') =>
  api.post(`/message/generate/${targetId}`, { channel }).then((r) => r.data)

export const generateBatch = (target_ids: number[], channel: 'email' | 'linkedin') =>
  api.post('/message/generate/batch', { target_ids, channel }).then((r) => r.data)

export const approveMessage = (id: number, body: string, subject?: string) =>
  api.patch(`/message/approve/${id}`, { body, subject }).then((r) => r.data)

export const deleteMessage = (id: number) =>
  api.delete(`/message/${id}`).then((r) => r.data)

export const sendEmail = (messageId: number) =>
  api.post(`/send/email/${messageId}`).then((r) => r.data)

export const sendLinkedIn = (messageId: number) =>
  api.post(`/send/linkedin/${messageId}`).then((r) => r.data)

export const sendBatch = (message_ids: number[]) =>
  api.post('/send/batch', { message_ids }).then((r) => r.data)

export const scheduleEmail = (messageId: number) =>
  api.post(`/send/email/${messageId}/schedule`).then((r) => r.data as { scheduled: boolean; scheduled_for_melbourne: string })

export const scheduleBatch = (message_ids: number[]) =>
  api.post('/send/batch/schedule', { message_ids }).then((r) => r.data)

export const exportTargets = (filter: 'all' | 'true' | 'false' = 'all') => {
  const params = filter !== 'all' ? `?has_open_roles=${filter}` : ''
  window.open(`/api/targets/export${params}`, '_blank')
}

export const fetchPersona = () =>
  api.get('/persona').then((r) => r.data as Persona)

export const savePersona = (data: Persona) =>
  api.post('/persona', data).then((r) => r.data)
