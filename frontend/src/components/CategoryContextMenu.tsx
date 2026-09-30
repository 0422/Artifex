import { useEffect, useRef } from 'react'
import { Pencil, Trash2 } from 'lucide-react'

/**
 * 2026-09-30 分类树右键上下文菜单。
 *
 * 侧边栏是四级窄树， hover 小按钮在深层节点上很难点准，
 * 故改用右键菜单承载「重命名 / 删除」。点击菜单外区域或按 Esc 关闭。
 */
export type CategoryMenuAction = 'rename' | 'delete'

export default function CategoryContextMenu({
  x,
  y,
  name,
  onAction,
  onClose,
}: {
  x: number
  y: number
  name: string
  onAction: (action: CategoryMenuAction) => void
  onClose: () => void
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) onClose()
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    // 捕获阶段监听：右键菜单自身也是 document 的点击目标
    document.addEventListener('mousedown', onPointerDown, true)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown, true)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [onClose])

  // 菜单贴边时翻转，避免超出视口
  const left = Math.min(x, window.innerWidth - 168)
  const top = Math.min(y, window.innerHeight - 96)

  return (
    <div
      ref={ref}
      role="menu"
      aria-label={`分类操作：${name}`}
      style={{ left, top }}
      className="fixed z-[80] w-40 overflow-hidden rounded-md border border-zinc-700 bg-zinc-900 py-1 shadow-2xl"
    >
      <button
        role="menuitem"
        onClick={() => onAction('rename')}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100"
      >
        <Pencil size={13} />重命名
      </button>
      <button
        role="menuitem"
        onClick={() => onAction('delete')}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-red-300 hover:bg-red-950/60"
      >
        <Trash2 size={13} />删除
      </button>
    </div>
  )
}
