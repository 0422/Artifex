import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { authApi } from '../services/api'
import { useAuthStore } from '../stores/authStore'

const NAV = [
  { to: '/capture', label: '内容捕获' },
  { to: '/path', label: '学习路径' },
]

export default function Layout() {
  const user = useAuthStore((s) => s.user)
  const clear = useAuthStore((s) => s.clear)
  const navigate = useNavigate()

  const logout = async () => {
    await authApi.logout().catch(() => {})
    clear()
    navigate('/auth')
  }

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 flex-col border-r border-slate-800 bg-slate-900/40 p-4">
        <div className="mb-8 px-2 text-lg font-semibold text-indigo-400">灵犀</div>
        <nav className="flex-1 space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm ${
                  isActive ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:bg-slate-800'
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-800 pt-3 text-xs text-slate-500">
          <div className="mb-2 truncate px-2">{user?.nickname || user?.email}</div>
          <button onClick={logout} className="px-2 text-slate-400 hover:text-slate-200">
            退出登录
          </button>
        </div>
      </aside>
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}
