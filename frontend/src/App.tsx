import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { authApi } from './services/api'
import { useAuthStore } from './stores/authStore'
import AuthPage from './pages/AuthPage'
import ChatPage from './pages/ChatPage'
// 2026-09-30 新增边缘设备管理模块
import EdgeDevicesPage from './pages/EdgeDevicesPage'
import ContainerLoadingCalculatorPage from './pages/ContainerLoadingCalculatorPage'
import DashboardPage from './pages/DashboardPage'
import Layout from './pages/Layout'
import KnowledgePage from './pages/KnowledgePage'
import ToolLibraryPage from './pages/ToolLibraryPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((state) => state.accessToken)
  return token ? <>{children}</> : <Navigate to="/auth" replace />
}

export default function App() {
  const token = useAuthStore((state) => state.accessToken)
  const user = useAuthStore((state) => state.user)
  const setUser = useAuthStore((state) => state.setUser)
  const clear = useAuthStore((state) => state.clear)
  const [booting, setBooting] = useState(() => Boolean(token && !user))

  useEffect(() => {
    if (token && !user) {
      authApi.me().then(setUser).catch(clear).finally(() => setBooting(false))
    }
  }, [token, user, setUser, clear])

  if (booting) return <div className="p-10 text-zinc-400">正在加载...</div>

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          {/* 2026-09-30 新增边缘设备管理模块 */}
          <Route path="/edge-devices" element={<EdgeDevicesPage />} />
          <Route path="/tools" element={<ToolLibraryPage />} />
          <Route path="/tools/container-loading-calculator" element={<ContainerLoadingCalculatorPage />} />
          {/* 2026-10-01 移除学习路径/内容捕获/引导流程及三个轻量工具，
              原 /tools/learning-path、/tools/content-capture、/tools/:toolId、
              /onboarding、/capture、/path 路由随之删除 */}
        </Route>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
