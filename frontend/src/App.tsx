import { useEffect, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { authApi } from './services/api'
import { useAuthStore } from './stores/authStore'
import AuthPage from './pages/AuthPage'
import Layout from './pages/Layout'
import OnboardingPage from './pages/OnboardingPage'
import CapturePage from './pages/CapturePage'
import PathPage from './pages/PathPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken)
  return token ? <>{children}</> : <Navigate to="/auth" replace />
}

export default function App() {
  const token = useAuthStore((s) => s.accessToken)
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const clear = useAuthStore((s) => s.clear)
  const [booting, setBooting] = useState(true)

  // 有 token 但无 user（刷新页面后），拉一次 /me 恢复用户信息
  useEffect(() => {
    if (token && !user) {
      authApi
        .me()
        .then(setUser)
        .catch(() => clear())
        .finally(() => setBooting(false))
    } else {
      setBooting(false)
    }
  }, [token, user, setUser, clear])

  if (booting) return <div className="p-10 text-slate-400">加载中…</div>

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/onboarding" element={<RequireAuth><OnboardingPage /></RequireAuth>} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route path="/capture" element={<CapturePage />} />
          <Route path="/path" element={<PathPage />} />
        </Route>
        <Route path="/" element={<Navigate to="/path" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
