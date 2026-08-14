import { http } from './http'
import type {
  AuthResponse,
  Capture,
  CaptureConceptsResponse,
  CaptureSourceType,
  Domain,
  LearningPath,
  OnboardingQuestion,
  User,
} from '../lib/types'

// ---- Auth ----
export const authApi = {
  register: (email: string, password: string, nickname?: string) =>
    http.post<AuthResponse>('/auth/register', { email, password, nickname }).then((r) => r.data),

  login: (email: string, password: string) =>
    http.post<AuthResponse>('/auth/login', { email, password }).then((r) => r.data),

  logout: () => http.post('/auth/logout').then((r) => r.data),

  me: () => http.get<User>('/auth/me').then((r) => r.data),
}

// ---- Capture ----
export const captureApi = {
  create: (domain: Domain, sourceType: CaptureSourceType, content?: string, sourceUrl?: string) =>
    http
      .post<Capture>('/capture', {
        domain,
        source_type: sourceType,
        content,
        source_url: sourceUrl,
      })
      .then((r) => r.data),

  uploadPdf: (domain: Domain, file: File) => {
    const form = new FormData()
    form.append('domain', domain)
    form.append('file', file)
    return http.post<Capture>('/capture/pdf', form).then((r) => r.data)
  },

  getStatus: (id: string) => http.get<Capture>(`/capture/${id}`).then((r) => r.data),

  getConcepts: (id: string) =>
    http.get<CaptureConceptsResponse>(`/capture/${id}/concepts`).then((r) => r.data),
}

// ---- Path ----
export const pathApi = {
  getOnboarding: () => http.get<OnboardingQuestion[]>('/path/onboarding').then((r) => r.data),

  completeOnboarding: (domain: Domain, answers: Record<string, string>) =>
    http
      .post<LearningPath>('/path/onboarding/complete', { domain, answers })
      .then((r) => r.data),

  getCurrent: () => http.get<LearningPath>('/path/current').then((r) => r.data),
}
