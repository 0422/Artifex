import { BarChart3, Languages, Library, LogOut, Route, ScanText } from 'lucide-react'
import { useRef, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { authApi } from '../services/api'
import { useAuthStore } from '../stores/authStore'

const NAV = [
  { to: '/chat', label: '情境对话', icon: Languages },
  { to: '/knowledge', label: '知识库', icon: Library },
  { to: '/dashboard', label: '仪表盘', icon: BarChart3 },
  { to: '/capture', label: '内容捕获', icon: ScanText },
  { to: '/path', label: '学习路径', icon: Route },
]

const SIDEBAR_WIDTH_KEY = 'artifex_sidebar_width'
const LEGACY_SIDEBAR_KEY = 'lingua_sidebar_collapsed'
const SIDEBAR_MIN_WIDTH = 72
const SIDEBAR_COLLAPSE_THRESHOLD = 160
const SIDEBAR_DEFAULT_WIDTH = 256
const SIDEBAR_MAX_WIDTH = 360

export default function Layout() {
  const user = useAuthStore((s) => s.user)
  const clear = useAuthStore((s) => s.clear)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const stored = Number(localStorage.getItem(SIDEBAR_WIDTH_KEY))
    if (Number.isFinite(stored) && stored >= SIDEBAR_MIN_WIDTH && stored <= SIDEBAR_MAX_WIDTH) return stored
    return localStorage.getItem(LEGACY_SIDEBAR_KEY) === 'true' ? SIDEBAR_MIN_WIDTH : SIDEBAR_DEFAULT_WIDTH
  })
  const [resizing, setResizing] = useState(false)
  const latestWidthRef = useRef(sidebarWidth)
  const navigate = useNavigate()
  const collapsed = sidebarWidth < SIDEBAR_COLLAPSE_THRESHOLD

  const updateSidebarWidth = (width: number) => {
    const next = Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, width))
    latestWidthRef.current = next
    setSidebarWidth(next)
  }

  const commitSidebarWidth = (width = latestWidthRef.current) => {
    const next = width < SIDEBAR_COLLAPSE_THRESHOLD ? SIDEBAR_MIN_WIDTH : Math.max(200, width)
    latestWidthRef.current = next
    setSidebarWidth(next)
    localStorage.setItem(SIDEBAR_WIDTH_KEY, String(next))
  }

  const logout = async () => {
    await authApi.logout().catch(() => undefined)
    clear()
    navigate('/auth')
  }

  return (
    <div className="flex h-[100dvh] min-h-0 bg-zinc-950 text-zinc-100">
      <aside style={{ width: sidebarWidth }} className={`relative hidden shrink-0 flex-col border-r border-zinc-800 bg-zinc-950 md:flex ${resizing ? '' : 'transition-[width]'}`}>
        <div className={`flex h-14 items-center border-b border-zinc-800 ${collapsed ? 'justify-center px-2' : 'px-4'}`}>
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-teal-500 text-sm font-semibold text-teal-300">李</span>
          {!collapsed && <span className="ml-3 whitespace-nowrap font-semibold">Artifex</span>}
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} title={collapsed ? label : undefined} className={({ isActive }) => `flex h-10 items-center rounded-md text-sm transition-colors ${collapsed ? 'justify-center px-0' : 'px-3'} ${isActive ? 'bg-teal-950 text-teal-300' : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100'}`}>
              <Icon className="shrink-0" size={18} />{!collapsed && <span className="ml-3 whitespace-nowrap">{label}</span>}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-zinc-800 p-3">
          {!collapsed && user?.nickname && <p className="mb-2 truncate px-3 text-xs text-zinc-500">{user.nickname}</p>}
          <button title="退出登录" onClick={logout} className={`flex h-10 w-full items-center rounded-md text-sm text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100 ${collapsed ? 'justify-center px-0' : 'px-3'}`}><LogOut className="shrink-0" size={18} />{!collapsed && <span className="ml-3">退出登录</span>}</button>
        </div>
        <div
          role="separator"
          aria-label="调整导航栏宽度"
          aria-orientation="vertical"
          aria-valuemin={SIDEBAR_MIN_WIDTH}
          aria-valuemax={SIDEBAR_MAX_WIDTH}
          aria-valuenow={Math.round(sidebarWidth)}
          tabIndex={0}
          title="拖动调整导航栏宽度"
          className="group absolute inset-y-0 -right-1 z-50 w-2 cursor-col-resize touch-none outline-none"
          onPointerDown={(event) => {
            event.currentTarget.setPointerCapture(event.pointerId)
            setResizing(true)
            document.body.style.cursor = 'col-resize'
            document.body.style.userSelect = 'none'
          }}
          onPointerMove={(event) => {
            if (!event.currentTarget.hasPointerCapture(event.pointerId)) return
            updateSidebarWidth(event.clientX)
          }}
          onPointerUp={(event) => {
            if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
            setResizing(false)
            document.body.style.cursor = ''
            document.body.style.userSelect = ''
            commitSidebarWidth()
          }}
          onPointerCancel={() => {
            setResizing(false)
            document.body.style.cursor = ''
            document.body.style.userSelect = ''
            commitSidebarWidth()
          }}
          onKeyDown={(event) => {
            if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
            event.preventDefault()
            const next = event.key === 'ArrowLeft'
              ? Math.max(SIDEBAR_MIN_WIDTH, sidebarWidth - 16)
              : collapsed ? SIDEBAR_DEFAULT_WIDTH : Math.min(SIDEBAR_MAX_WIDTH, sidebarWidth + 16)
            updateSidebarWidth(next)
            commitSidebarWidth(next)
          }}
        >
          <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-transparent transition-colors group-hover:bg-teal-500 group-focus:bg-teal-500" />
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-auto pb-14 md:pb-0"><Outlet /></main>

      <nav className="fixed inset-x-0 bottom-0 z-30 flex h-14 border-t border-zinc-800 bg-zinc-950 md:hidden">
        {NAV.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => `flex flex-1 flex-col items-center justify-center gap-1 text-[10px] ${isActive ? 'text-teal-300' : 'text-zinc-500'}`}><Icon size={18} /><span>{label}</span></NavLink>)}
      </nav>
    </div>
  )
}
