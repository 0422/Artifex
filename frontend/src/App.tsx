import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { authApi } from './services/api'
import { useAuthStore } from './stores/authStore'
import AuthPage from './pages/AuthPage'
import CapturePage from './pages/CapturePage'
import ChatPage from './pages/ChatPage'
import DashboardPage from './pages/DashboardPage'
import Layout from './pages/Layout'
import KnowledgePage from './pages/KnowledgePage'
import OnboardingPage from './pages/OnboardingPage'
import PathPage from './pages/PathPage'

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
        <Route path="/onboarding" element={<RequireAuth><OnboardingPage /></RequireAuth>} />
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/capture" element={<CapturePage />} />
          <Route path="/path" element={<PathPage />} />
        </Route>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
