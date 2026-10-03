// 与后端 Pydantic schema 对应的类型定义

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

// 2026-10-01 内容捕获（Capture/Concept/RelatedConcept/CaptureConceptsResponse）与
// 学习路径、5 分钟引导（OnboardingQuestion/StartingPointReport/Milestone/LearningPath）类型随功能下线删除

// ---- LLM 供应商（2026-10-01 新增）----
// json_mode 控制是否发送 response_format；思考类模型（如 deepseek-reasoner）常不支持，需关闭
export interface LLMModel {
  name: string
  json_mode: boolean
}

export interface LLMProvider {
  id: string
  name: string
  base_url: string
  // 后端只返回掩码，不明文返回 API Key
  api_key_masked: string
  active_model: string | null
  models: LLMModel[]
  // 内置供应商（中转站/DeepSeek/StepFun）锁定，不可删除
  builtin: boolean
}

export interface LLMProvidersResponse {
  active_provider_id: string | null
  active_model: string | null
  providers: LLMProvider[]
}

export interface LLMProviderInput {
  name: string
  base_url: string
  api_key: string
  // 换行或逗号分隔的模型名，前端负责拆分
  models: string[]
}

export interface LLMProviderUpdate {
  name?: string
  base_url?: string
  // 留空表示不修改已保存的 API Key（后端只回掩码，前端编辑框默认为空）
  api_key?: string
  models?: LLMModel[]
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
  // 2026-09-30 官方共享分类（雅思真题库）为 true，前端据此隐藏编辑/删除入口
  is_shared: boolean
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
  // 2026-09-30 雅思口语场景库：ielts_part 非空即雅思场景，
  // 决定对话走考官 prompt（Part 1 逐题追问 / Part 2 题卡独白 / Part 3 抽象追问）
  ielts_part: number | null
  // Part 2 的题卡正文，UI 单独展示，不混在 description 里
  cue_card: string | null
  // 2026-09-30 官方共享真题为 true，前端据此隐藏编辑/删除入口
  is_shared: boolean
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
  ielts_part?: number | null
  cue_card?: string | null
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
  | { type: 'ai_response'; message_id: string; content: string; created_at: string; degraded: boolean; degraded_reason?: string | null }
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

// ---- Edge devices ----
// 2026-09-30 新增边缘设备管理模块：设备在线状态。unknown = 档案刚建、尚未扫描过
export type EdgeDeviceStatus = 'online' | 'offline' | 'unknown'

// OTA 任务生命周期
export type EdgeOtaTaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'canceled'

export const EDGE_DEVICE_CHIPS = ['esp32s3', 'rk3576', 'esp32', 'esp32c3'] as const
export type EdgeChip = (typeof EDGE_DEVICE_CHIPS)[number]

// llm_config.api_key 由后端脱敏后返回，只用于展示，不是真实密钥
export interface EdgeLlmConfig {
  api_key: string | null
  base_url: string | null
  model: string | null
  temperature: number | null
}

export interface EdgePromptConfig {
  system_prompt: string | null
}

export interface EdgeDeviceBrief {
  id: string
  name: string
  chip: string
  ip_address: string | null
}

export interface EdgeDevice extends EdgeDeviceBrief {
  mac_address: string | null
  firmware_version: string | null
  status: EdgeDeviceStatus
  last_online_at: string | null
  wifi_ssid: string | null
  llm_config: EdgeLlmConfig | null
  prompt_config: EdgePromptConfig | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface EdgeDeviceInput {
  name: string
  chip: string
  ip_address?: string | null
  mac_address?: string | null
  firmware_version?: string | null
  notes?: string | null
}

export interface EdgeWifiInput {
  ssid: string
  password: string
}

export interface EdgePromptInput {
  system_prompt: string
}

// 下发 LLM 配置。api_key 省略或保持脱敏值（**** 开头）时，后端沿用已保存的真值
export interface EdgeLlmInput {
  api_key?: string | null
  base_url?: string | null
  model?: string | null
  temperature?: number | null
}

/** 扫描到的未认领设备：固件只广播裸 IP，认领后才能补充名称/芯片等元数据 */
export interface DiscoveredDevice {
  ip: string
  payload: string
  seen_count: number
}

/** 已建档设备在本次扫描中的在线情况 */
export interface DeviceScanState {
  device_id: string
  name: string
  ip_address: string | null
  online: boolean
  payload: string | null
}

export interface EdgeScanResult {
  scanned_at: string
  duration_ms: number
  port: number
  unclaimed: DiscoveredDevice[]
  matched: DeviceScanState[]
}

export interface EdgeFirmware {
  id: string
  filename: string
  version: string
  chip: string
  size_bytes: number
  sha256: string
  notes: string | null
  created_at: string
}

export interface EdgeOtaTask {
  id: string
  device_id: string
  firmware_id: string | null
  status: EdgeOtaTaskStatus
  progress: number
  error: string | null
  log: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  firmware: EdgeFirmware | null
}

// ---- 世势洞察（2026-10-03 新增 M6 模块）----
// 新闻板块与后端 app/models/enums.py 的 NewsDomain 对应
export type NewsDomain = 'ai' | 'tech' | 'finance' | 'education' | 'world' | 'general'

export const NEWS_DOMAIN_LABELS: Record<NewsDomain, string> = {
  ai: 'AI',
  tech: '科技',
  finance: '财经',
  education: '教育',
  world: '国际',
  general: '综合',
}

export interface NewsSource {
  id: string
  name: string
  url: string
  domain: NewsDomain
  is_enabled: boolean
  last_fetched_at: string | null
  // 最近一次抓取失败原因（截断 200 字），来源管理弹窗里展示
  last_error: string | null
  created_at: string
  updated_at: string
}

export interface NewsSourceInput {
  name: string
  url: string
  domain: NewsDomain
}

export interface NewsArticle {
  id: string
  source_id: string
  domain: NewsDomain
  title: string
  url: string
  excerpt: string | null
  published_at: string | null
  created_at: string
  source_name: string
}

// LLM 日报里的单条策展结果。importance 为 0 表示降级稿的原始标题占位
export interface NewsDigestItem {
  headline: string
  summary_zh: string
  why_matters: string
  importance: number
  url: string
  source_name: string
  published_at: string | null
}

export interface NewsDigestListItem {
  id: string
  digest_date: string
  domain: NewsDomain
  title: string
  article_count: number
  degraded: boolean
  created_at: string
}

export interface NewsDigest extends NewsDigestListItem {
  summary: string
  items: NewsDigestItem[]
}

export interface NewsDigestPage {
  items: NewsDigestListItem[]
  total: number
  page: number
  page_size: number
}

export interface NewsArticlePage {
  items: NewsArticle[]
  total: number
  page: number
  page_size: number
}

export interface NewsFetchResult {
  total_sources: number
  succeeded: number
  failed: number
  new_articles: number
}

export interface NewsDigestGenerateInput {
  domain?: NewsDomain
  digest_date?: string
}
