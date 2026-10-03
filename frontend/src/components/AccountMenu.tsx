import { useEffect, useRef } from 'react'
import { HelpCircle, LogOut, Settings, Sparkles } from 'lucide-react'

/**
 * 2026-10-01 左上角「李」字头像点击弹出的账号菜单。
 *
 * 参考飞书的账号菜单结构：顶部头像 + 昵称，下面分组罗列功能项，最后用分隔线
 * 把退出登录隔开。原侧边栏底部的昵称与退出登录整块已移除，退出登录移到这里。
 */

export type AccountMenuAction = 'llm' | 'settings' | 'help' | 'logout'

const MENU_ITEMS: { action: AccountMenuAction; label: string; hint?: string; icon: typeof Sparkles }[] = [
  { action: 'llm', label: 'LLM Select', hint: '切换 LLM 供应商与模型', icon: Sparkles },
  { action: 'settings', label: '设置', icon: Settings },
  { action: 'help', label: '帮助', icon: HelpCircle },
]

export default function AccountMenu({
  nickname,
  activeLabel,
  onAction,
  onClose,
  className = 'left-3 top-[3.25rem]',
}: {
  nickname: string | null | undefined
  /** 当前生效的「供应商 / 模型」，展示在 LLM Select 项下方 */
  activeLabel: string
  onAction: (action: AccountMenuAction) => void
  onClose: () => void
  /** 定位：桌面端挂在侧边栏头像下方，移动端挂在底部导航上方 */
  className?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  // 用 ref 存最新的 onClose，这样监听器只需挂一次，不必因父组件重渲染而反复摘挂
  const closeRef = useRef(onClose)
  useEffect(() => {
    closeRef.current = onClose
  }, [onClose])

  useEffect(() => {
    const onDocumentClick = (event: MouseEvent) => {
      // 只在"点击菜单之外的区域"时收起。
      // 用 click 的冒泡阶段而不是 mousedown 的捕获阶段：菜单项自身的 click 一定先于
      // document 上的这个处理器执行，不会被提前卸载而丢失点击。
      if (ref.current && !ref.current.contains(event.target as Node)) closeRef.current()
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      // 输入框里不响应 Esc：中文输入法选词时也会派发 Escape
      const el = event.target as HTMLElement | null
      if (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) return
      closeRef.current()
    }

    // 延迟一帧再挂 click 监听：打开菜单的那次 click 还在派发中，
    // 立刻挂上会被同一个事件判成"点在窗外"而把菜单马上关掉。
    const timer = window.setTimeout(() => document.addEventListener('click', onDocumentClick), 0)

    return () => {
      window.clearTimeout(timer)
      document.removeEventListener('click', onDocumentClick)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [])

  return (
    <div
      ref={ref}
      role="menu"
      aria-label="账号菜单"
      className={`fixed z-[60] w-64 overflow-hidden rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl ${className}`}
    >
      {/* 账号信息头：与侧边栏顶部的「李」字头像呼应 */}
      <div className="flex items-center gap-3 border-b border-zinc-800 px-4 py-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-teal-500 text-sm font-semibold text-teal-300">
          李
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-zinc-100">{nickname || '未命名用户'}</p>
          {/* 供应商名 + 模型名可能很长，换行显示而不是截断，避免看不出当前用的是哪家 */}
          <p className="mt-0.5 break-words text-xs leading-4 text-zinc-400">
            <span className="text-zinc-400">当前 LLM </span>
            {activeLabel}
          </p>
        </div>
      </div>

      <div className="py-1">
        {MENU_ITEMS.map(({ action, label, hint, icon: Icon }) => (
          <button
            key={action}
            role="menuitem"
            onClick={() => onAction(action)}
            className="flex w-full items-start gap-2.5 px-4 py-2 text-left hover:bg-zinc-800"
          >
            <Icon size={15} className="mt-0.5 shrink-0 text-zinc-400" />
            <span className="min-w-0">
              <span className="block text-sm text-zinc-200">{label}</span>
              {hint && <span className="block text-xs text-zinc-400">{hint}</span>}
            </span>
          </button>
        ))}
      </div>

      <div className="border-t border-zinc-800 py-1">
        <button
          role="menuitem"
          onClick={() => onAction('logout')}
          className="flex w-full items-center gap-2.5 px-4 py-2 text-left text-sm text-red-300 hover:bg-red-950/60"
        >
          <LogOut size={15} className="shrink-0" />
          退出登录
        </button>
      </div>
    </div>
  )
}
