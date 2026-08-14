// 与后端 Pydantic schema 对应的类型定义

export type Domain = 'language' | 'humanities' | 'skill'
export type CaptureSourceType = 'text' | 'url' | 'pdf'
export type CaptureStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type MilestoneStatus = 'completed' | 'current' | 'locked'

export interface User {
  id: string
  email: string
  nickname: string | null
  avatar_url: string | null
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

// ---- Capture ----
export interface Capture {
  id: string
  domain: Domain
  source_type: CaptureSourceType
  source_url: string | null
  summary: string | null
  status: CaptureStatus
  created_at: string
}

export interface RelatedConcept {
  id: string
  label: string
}

export interface Concept {
  id: string
  label: string
  definition: string | null
  domain: Domain
  related: RelatedConcept[]
  card_count: number
}

export interface CaptureConceptsResponse {
  capture: Capture
  concepts: Concept[]
}

// ---- Path ----
export interface OnboardingQuestion {
  key: string
  question: string
  hint: string | null
}

export interface StartingPointReport {
  level_summary?: string
  strengths?: string[]
  gaps?: string[]
  recommendation?: string
}

export interface Milestone {
  id: string
  order_index: number
  title: string
  description: string | null
  status: MilestoneStatus
  progress_data: Record<string, unknown> | null
}

export interface LearningPath {
  id: string
  domain: Domain
  title: string
  starting_point_report: StartingPointReport | null
  status: string
  created_at: string
  milestones: Milestone[]
}
