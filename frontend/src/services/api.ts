import { http } from './http'
import type {
  AuthResponse,
  Capture,
  CaptureConceptsResponse,
  CaptureSourceType,
  Domain,
  LearningPath,
  KnowledgeCategory,
  KnowledgeCategoryInput,
  OnboardingQuestion,
  DashboardOverview,
  DashboardSessionDetail,
  DashboardSessionPage,
  EdgeDevice,
  EdgeDeviceInput,
  EdgeFirmware,
  EdgeLlmInput,
  EdgeOtaTask,
  EdgePromptInput,
  EdgeScanResult,
  EdgeWifiInput,
  Scenario,
  ScenarioInput,
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

// ---- Scenarios ----
export const scenarioApi = {
  list: (includeInactive = false, filters?: { domain?: string; category_id?: string; q?: string }) =>
    http.get<Scenario[]>('/scenarios', { params: { include_inactive: includeInactive, ...filters } }).then((r) => r.data),

  create: (input: ScenarioInput) =>
    http.post<Scenario>('/scenarios', input).then((r) => r.data),

  update: (id: string, input: Partial<ScenarioInput>) =>
    http.put<Scenario>(`/scenarios/${id}`, input).then((r) => r.data),

  remove: (id: string) => http.delete(`/scenarios/${id}`),
}

// ---- Knowledge library ----
export const knowledgeApi = {
  categoryTree: () =>
    http.get<KnowledgeCategory[]>('/knowledge/categories/tree').then((r) => r.data),

  createCategory: (input: KnowledgeCategoryInput) =>
    http.post<KnowledgeCategory>('/knowledge/categories', input).then((r) => r.data),

  updateCategory: (id: string, input: Partial<KnowledgeCategoryInput>) =>
    http.put<KnowledgeCategory>(`/knowledge/categories/${id}`, input).then((r) => r.data),

  archiveCategory: (id: string) => http.delete(`/knowledge/categories/${id}`),
}

// ---- Dashboard ----
export const dashboardApi = {
  overview: () => http.get<DashboardOverview>('/dashboard/overview').then((r) => r.data),

  sessions: (page = 1, pageSize = 20) =>
    http.get<DashboardSessionPage>('/dashboard/sessions', { params: { page, page_size: pageSize } }).then((r) => r.data),

  session: (id: string) =>
    http.get<DashboardSessionDetail>(`/dashboard/sessions/${id}`).then((r) => r.data),
}

// ---- Edge devices ----
// 2026-09-30 新增边缘设备管理模块。固件侧尚无 OTA/远程配置接口，
// 下发类请求会由后端返回 device-ota-unsupported / device-api-unsupported 等错误码。
export const edgeDevicesApi = {
  list: () => http.get<EdgeDevice[]>('/edge-devices').then((r) => r.data),

  create: (input: EdgeDeviceInput) =>
    http.post<EdgeDevice>('/edge-devices', input).then((r) => r.data),

  update: (id: string, input: Partial<EdgeDeviceInput>) =>
    http.patch<EdgeDevice>(`/edge-devices/${id}`, input).then((r) => r.data),

  remove: (id: string) => http.delete(`/edge-devices/${id}`),

  // 触发一次局域网 UDP 扫描，返回未认领 IP 与已建档设备的在线情况
  scan: () => http.post<EdgeScanResult>('/edge-devices/scan').then((r) => r.data),

  defaultPrompt: () =>
    http.get<{ system_prompt: string }>('/edge-devices/default-prompt').then((r) => r.data),

  pushWifi: (id: string, input: EdgeWifiInput) =>
    http.put<EdgeDevice>(`/edge-devices/${id}/wifi`, input).then((r) => r.data),

  pushLlmConfig: (id: string, input: EdgeLlmInput) =>
    http.put<EdgeDevice>(`/edge-devices/${id}/llm-config`, input).then((r) => r.data),

  pushPrompt: (id: string, input: EdgePromptInput) =>
    http.put<EdgeDevice>(`/edge-devices/${id}/prompt`, input).then((r) => r.data),

  // ---- Firmware warehouse ----
  firmwareList: () =>
    http.get<EdgeFirmware[]>('/edge-devices/firmware').then((r) => r.data),

  uploadFirmware: (file: File, version: string, chip: string, notes?: string) => {
    const form = new FormData()
    form.append('version', version)
    form.append('chip', chip)
    form.append('file', file)
    if (notes) form.append('notes', notes)
    return http.post<EdgeFirmware>('/edge-devices/firmware', form).then((r) => r.data)
  },

  deleteFirmware: (id: string) => http.delete(`/edge-devices/firmware/${id}`),

  downloadFirmware: (id: string) =>
    http.get(`/edge-devices/firmware/${id}/download`, { responseType: 'blob' }).then((r) => r.data),

  // ---- OTA tasks ----
  otaTasks: (deviceId?: string) =>
    http
      .get<EdgeOtaTask[]>('/edge-devices/ota-tasks', { params: { device_id: deviceId } })
      .then((r) => r.data),

  otaTask: (id: string) =>
    http.get<EdgeOtaTask>(`/edge-devices/ota-tasks/${id}`).then((r) => r.data),

  createOtaTask: (deviceId: string, firmwareId: string) =>
    http
      .post<EdgeOtaTask>(`/edge-devices/${deviceId}/ota-tasks`, { firmware_id: firmwareId })
      .then((r) => r.data),

  cancelOtaTask: (id: string) =>
    http.post<EdgeOtaTask>(`/edge-devices/ota-tasks/${id}/cancel`).then((r) => r.data),
}
