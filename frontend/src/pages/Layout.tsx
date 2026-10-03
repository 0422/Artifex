import { BarChart3, Cpu, Languages, Library, Newspaper, Wrench } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import AccountMenu, { type AccountMenuAction } from '../components/AccountMenu'
import InfoDialog from '../components/InfoDialog'
import LlmSelectDialog from '../components/LlmSelectDialog'
import ToastHost from '../components/ToastHost'
import { authApi, llmApi } from '../services/api'
// 2026-09-29 产品名改由 constants.ts 的 PRODUCT_NAME 统一提供
import { PRODUCT_NAME } from '../lib/constants'
import { useAuthStore } from '../stores/authStore'

// 2026-10-01 侧边栏自上而下调整为：仪表盘、情境对话、边缘设备、知识库、工具库；
// 同时「边缘管理」更名为「边缘设备」。侧边栏与移动端底部导航共用本数组。
// 2026-10-03 末尾追加「世势洞察」（M6 新闻日报模块），既有顺序未动。
const NAV = [
  { to: '/dashboard', label: '仪表盘', icon: BarChart3 },
  { to: '/chat', label: '情境对话', icon: Languages },
  { to: '/edge-devices', label: '边缘设备', icon: Cpu },
  { to: '/knowledge', label: '知识库', icon: Library },
  { to: '/tools', label: '工具库', icon: Wrench },
  { to: '/news', label: '世势洞察', icon: Newspaper },
]

const SIDEBAR_WIDTH_KEY = 'artifex_sidebar_width'
const LEGACY_SIDEBAR_KEY = 'lingua_sidebar_collapsed'
const SIDEBAR_MIN_WIDTH = 72
const SIDEBAR_COLLAPSE_THRESHOLD = 160
const SIDEBAR_DEFAULT_WIDTH = 256
const SIDEBAR_MAX_WIDTH = 360

// 2026-10-01 桌面端菜单挂在侧边栏头像下方，移动端挂在底部导航上方
// 2026-10-02 全卡片式改版：窗口加了 p-1.5，头像整体下移 6px，菜单位置同步由 top-[3.25rem] 调为 top-[3.625rem]
const DESKTOP_MENU_CLASS = 'left-3 top-[3.625rem]'
const MOBILE_MENU_CLASS = 'bottom-16 left-3'

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(min-width: 768px)').matches,
  )
  useEffect(() => {
    const query = window.matchMedia('(min-width: 768px)')
    const onChange = () => setIsDesktop(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])
  return isDesktop
}

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
  const location = useLocation()
  const collapsed = sidebarWidth < SIDEBAR_COLLAPSE_THRESHOLD

  // 2026-10-01 账号菜单与 LLM Select 弹窗
  const [menuOpen, setMenuOpen] = useState(false)
  const [dialog, setDialog] = useState<'none' | 'llm' | 'settings' | 'help'>('none')
  const [activeLlm, setActiveLlm] = useState('加载中...')
  const isDesktop = useIsDesktop()

  // 菜单里展示当前生效的 LLM，切供应商后由 LlmSelectDialog 回调刷新
  useEffect(() => {
    let alive = true
    llmApi
      .list()
      .then((data) => {
        if (!alive) return
        const provider = data.providers.find((p) => p.id === data.active_provider_id)
        setActiveLlm(provider && data.active_model ? `${provider.name} · ${data.active_model}` : '未配置')
      })
      .catch(() => alive && setActiveLlm('未配置'))
    return () => {
      alive = false
    }
  }, [dialog])

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
    // 2026-10-02 全卡片式改版：窗口四周留 6px 内边距、各区域间留 6px 间隙，
    // 侧边栏/内容区各自成为带边框圆角的独立面板（原为 flex h-[100dvh] min-h-0 bg-zinc-950 text-zinc-100，区域紧贴、仅竖线分隔）
    <div className="flex h-[100dvh] min-h-0 gap-1.5 bg-zinc-950 p-1.5 text-zinc-100">
      {/* 2026-10-02 全卡片式改版：侧边栏由「通栏 + 右侧竖线」改为独立面板。
          原 className：relative hidden shrink-0 flex-col border-r border-zinc-800 bg-zinc-950 md:flex，边框/底色改由 panel 类提供 */}
      <aside style={{ width: sidebarWidth }} className={`panel relative hidden shrink-0 flex-col md:flex ${resizing ? '' : 'transition-[width]'}`}>
        <div className={`flex h-14 items-center border-b border-zinc-800 ${collapsed ? 'justify-center px-2' : 'px-4'}`}>
          {/* 2026-10-01 「李」字改为账号菜单入口：LLM Select / 设置 / 帮助 / 退出登录 */}
          <button
            title="账号菜单"
            aria-label="账号菜单"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-colors ${menuOpen ? 'border-teal-400 bg-teal-950 text-teal-200' : 'border-teal-500 text-teal-300 hover:bg-teal-950/60'}`}
          >
            李
          </button>
          {!collapsed && <span className="ml-3 whitespace-nowrap font-semibold">{PRODUCT_NAME}</span>}
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            // 2026-10-02 全卡片式改版：侧边栏面板底色为 zinc-900，原 hover:bg-zinc-900 会与底色重合，改为 zinc-800
            // 2026-10-02 第三批：active 态补左侧 2px teal 指示条（before: 伪元素）。
            // 原来只有底色一个通道，弱视觉环境下"当前在哪"不够醒目；指示条与底色双通道编码
            <NavLink key={to} to={to} title={collapsed ? label : undefined} className={({ isActive }) => `relative flex h-10 items-center rounded-md text-sm transition-colors ${collapsed ? 'justify-center px-0' : 'px-3'} ${isActive ? 'bg-teal-950 text-teal-300 before:absolute before:left-0 before:top-1/2 before:h-5 before:w-0.5 before:-translate-y-1/2 before:rounded-full before:bg-teal-400' : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100'}`}>
              <Icon className="shrink-0" size={18} />{!collapsed && <span className="ml-3 whitespace-nowrap">{label}</span>}
            </NavLink>
          ))}
        </nav>
        {/* 2026-10-01 原侧边栏底部的昵称与「退出登录」整块已移除：
            昵称改由左上角账号菜单展示，退出登录移入该菜单。 */}

        <div
          role="separator"
          aria-label="调整导航栏宽度"
          aria-orientation="vertical"
          aria-valuemin={SIDEBAR_MIN_WIDTH}
          aria-valuemax={SIDEBAR_MAX_WIDTH}
          aria-valuenow={Math.round(sidebarWidth)}
          tabIndex={0}
          title="拖动调整导航栏宽度"
          // 2026-10-02 全卡片式改版：分隔条 inset-y-0 → inset-y-2，避免 hover/focus 高亮线在面板圆角处探出卡片
          className="group absolute inset-y-2 -right-1 z-50 w-2 cursor-col-resize touch-none outline-none"
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

      {/* 2026-10-02 全卡片式改版：main 本身不设卡片，由各页面自行渲染面板；
          移动端底部导航改为悬浮卡片（高 48px + 底部 6px）后，主区域预留空间 pb-14 → pb-16。
          2026-10-02 第二批：内层 div 以路径为 key，路由切换即重播 animate-page-in（淡入 + 上移），
          原来换页是硬切、没有任何过渡 */}
      <main className="min-w-0 flex-1 overflow-auto pb-16 md:pb-0">
        <div key={location.pathname} className="h-full animate-page-in"><Outlet /></div>
      </main>

      {/* 2026-10-02 全卡片式改版：底部导航由贴边通栏（fixed inset-x-0 bottom-0 h-14 border-t bg-zinc-950）
          改为悬浮圆角小卡片：四边内缩 6px，高度 h-14 → h-12 */}
      <nav className="fixed inset-x-1.5 bottom-1.5 z-30 flex h-12 rounded-lg border border-zinc-800 bg-zinc-900 md:hidden">
        {/* 2026-10-01 桌面侧边栏在移动端是隐藏的，账号菜单入口一并补到底部导航，
            否则手机上无法退出登录、也无法切 LLM */}
        <button
          title="账号菜单"
          aria-label="账号菜单"
          onClick={() => setMenuOpen((open) => !open)}
          className="flex w-14 shrink-0 items-center justify-center"
        >
          <span
            className={`flex h-7 w-7 items-center justify-center rounded-full border text-sm font-semibold ${menuOpen ? 'border-teal-400 bg-teal-950 text-teal-200' : 'border-teal-500 text-teal-300'}`}
          >
            李
          </span>
        </button>
        {NAV.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} className={({ isActive }) => `flex flex-1 flex-col items-center justify-center gap-1 text-[10px] ${isActive ? 'text-teal-300' : 'text-zinc-400'}`}><Icon size={18} /><span>{label}</span></NavLink>)}
      </nav>

      {/* 2026-10-02 全局 toast 宿主：挂在 window 根下，跨页面常驻 */}
      <ToastHost />

      {/* 2026-10-02 账号菜单：只渲染一个实例。
          早期写法同时挂了桌面（hidden md:block）与移动（md:hidden）两份，两个实例各自注册
          document 级 mousedown 监听，点桌面菜单项时被那个 display:none 的实例判定为
          "点在窗外"而提前卸载菜单，click 再也到不了按钮上，表现为点什么都不响应。 */}
      {menuOpen && (
        <AccountMenu
          className={isDesktop ? DESKTOP_MENU_CLASS : MOBILE_MENU_CLASS}
          nickname={user?.nickname}
          activeLabel={activeLlm}
          onAction={(action: AccountMenuAction) => {
            setMenuOpen(false)
            if (action === 'logout') {
              void logout()
              return
            }
            setDialog(action)
          }}
          onClose={() => setMenuOpen(false)}
        />
      )}

      {/* 2026-10-01 账号菜单拉起的三个弹窗。设置与帮助暂为占位，内容待补充 */}
      {dialog === 'llm' && (
        <LlmSelectDialog
          onClose={() => {
            // 诊断：若弹窗在没有用户操作的情况下消失，这里会打出调用栈，便于定位
            console.info('[llm-dialog] close', new Error('stack').stack)
            setDialog('none')
          }}
        />
      )}
      {dialog === 'settings' && (
        <InfoDialog title="设置" message="🚧 待补充：将提供账号信息、学习偏好等设置项。" onClose={() => setDialog('none')} />
      )}
      {dialog === 'help' && (
        <InfoDialog
          title="帮助"
          message={'🚧 待补充：使用说明与常见问题。\n\n当前版本可用功能：\n· 仪表盘 — 查看对话练习进度与薄弱点\n· 情境对话 — 与 AI 进行场景对话练习\n· 边缘设备 — 局域网设备扫描、认领与 OTA\n· 知识库 — 分类树与场景卡管理\n· 工具库 — 集装箱装载计算器\n· 左上角「李」→ LLM Select — 切换或新增 LLM 供应商'}
          onClose={() => setDialog('none')}
        />
      )}
    </div>
  )
}
