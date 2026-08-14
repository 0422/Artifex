import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { useAuthStore } from '../stores/authStore'

// baseURL 用 /api/v1，开发环境由 vite 代理转发到后端 8000
export const http = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // 携带 httpOnly refresh_token cookie
})

// 请求拦截：注入 access token
http.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：401 时用 refresh cookie 换新 token 重试一次
let refreshing: Promise<string> | null = null

async function doRefresh(): Promise<string> {
  const resp = await axios.post<{ access_token: string }>(
    '/api/v1/auth/refresh',
    {},
    { withCredentials: true },
  )
  const token = resp.data.access_token
  useAuthStore.getState().setAccessToken(token)
  return token
}

http.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean }
    const isAuthEndpoint = original?.url?.includes('/auth/')

    if (error.response?.status === 401 && original && !original._retried && !isAuthEndpoint) {
      original._retried = true
      try {
        refreshing = refreshing ?? doRefresh()
        const token = await refreshing
        refreshing = null
        original.headers.Authorization = `Bearer ${token}`
        return http(original)
      } catch {
        refreshing = null
        useAuthStore.getState().clear()
      }
    }
    return Promise.reject(error)
  },
)
