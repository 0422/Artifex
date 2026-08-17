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

// ---- Scenario practice ----
export type ScenarioLanguage = 'en' | 'ja' | 'zh'
export type ScenarioDifficulty =
  | 'beginner' | 'intermediate' | 'advanced'
  | 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2'
  | 'N5' | 'N4' | 'N3' | 'N2' | 'N1'
export type ScenarioMode = 'role_play' | 'guided_discussion' | 'socratic_dialogue' | 'debate' | 'source_analysis' | 'work_analysis'

export interface KnowledgeCategoryBrief {
  id: string
  name: string
  domain: string
  parent_id: string | null
}

export interface KnowledgeCategory extends KnowledgeCategoryBrief {
  description: string | null
  sort_order: number
  is_active: boolean
  card_count: number
  children: KnowledgeCategory[]
  created_at: string
  updated_at: string
}

export interface KnowledgeCategoryInput {
  name: string
  parent_id?: string | null
  domain: string
  description?: string | null
}

export interface Scenario {
  id: string
  title: string
  description: string
  language: ScenarioLanguage
  difficulty: ScenarioDifficulty
  domain: string
  scenario_mode: ScenarioMode
  estimated_minutes: number | null
  tags: string[]
  categories: KnowledgeCategoryBrief[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ScenarioInput {
  title: string
  description: string
  language: ScenarioLanguage
  difficulty: ScenarioDifficulty
  domain?: string
  scenario_mode?: ScenarioMode
  estimated_minutes?: number | null
  tags?: string[]
  category_ids?: string[]
}

export interface ChatCorrection {
  original: string
  corrected: string
  severity: 'minor' | 'major'
  explanation: string
}

export interface WeakPoint {
  category: 'vocabulary' | 'grammar' | 'expression' | 'pragmatics'
  tag: string
  description: string
  example: string
  suggestion: string
}

export interface SessionReport {
  summary: string
  weak_points: WeakPoint[]
  suggestions: string[]
  performance_score: number | null
  no_prominent_issues: boolean
  degraded: boolean
  insufficient_data: boolean
}

export type ChatServerEvent =
  | { type: 'authenticated'; user_id: string }
  | { type: 'session_started'; session_id: string; scenario_id: string; scenario_title: string; language: ScenarioLanguage; difficulty: ScenarioDifficulty; started_at: string }
  | { type: 'ai_response'; message_id: string; content: string; created_at: string; degraded: boolean }
  | ({ type: 'correction'; message_id: string } & ChatCorrection)
  | { type: 'session_ended'; session_id: string; duration_seconds: number; ended_at: string }
  | { type: 'report_generating'; session_id: string }
  | { type: 'session_report'; session_id: string; report: SessionReport }
  | { type: 'error'; code: string; message: string; recoverable: boolean }

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
  degraded?: boolean
  correction?: ChatCorrection
}

// ---- Dashboard ----
export type ReportStatus = 'ready' | 'degraded' | 'insufficient_data' | 'missing' | 'invalid'

export interface ScenarioDistributionItem {
  scenario_id: string | null
  title: string
  count: number
}

export interface WeakPointFrequency {
  tag: string
  category: string
  count: number
}

export interface DashboardOverview {
  total_conversations: number
  total_duration_seconds: number
  scored_conversations: number
  average_performance_score: number | null
  scenario_distribution: ScenarioDistributionItem[]
  frequent_weak_points: WeakPointFrequency[]
}

export interface DashboardSessionItem {
  id: string
  scenario_id: string | null
  scenario_title: string
  language: string
  difficulty: string | null
  duration_seconds: number
  performance_score: number | null
  weak_points_count: number
  report_status: ReportStatus
  created_at: string
  ended_at: string | null
}

export interface DashboardSessionPage {
  items: DashboardSessionItem[]
  total: number
  page: number
  page_size: number
}

export interface DashboardSessionDetail extends DashboardSessionItem {
  report: SessionReport | null
}
