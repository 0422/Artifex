import { AlertTriangle } from 'lucide-react'

/**
 * 2026-09-30 删除确认弹窗。
 *
 * 知识与雅思题库的删除都是"软删除"（后端置 is_active=False），数据不会真丢，
 * 但界面上即刻消失且目前没有恢复入口，所以破坏性操作一律先确认。
 */
export default function ConfirmDialog({
  title,
  message,
  confirmLabel = '删除',
  busy = false,
  onConfirm,
  onCancel,
}: {
  title: string
  message: string
  confirmLabel?: string
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 z-[70] grid place-items-center bg-black/70 p-4">
      <div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl">
        <header className="flex items-center gap-2 border-b border-zinc-800 p-4">
          <AlertTriangle className="text-amber-400" size={18} />
          <h2 className="font-semibold">{title}</h2>
        </header>
        <div className="space-y-3 p-5">
          <p className="whitespace-pre-wrap text-sm leading-6 text-zinc-300">{message}</p>
          <p className="text-xs leading-5 text-zinc-500">
            删除后该内容将不再显示，官方题库不可删除。如需找回，请联系开发者直接改库。
          </p>
        </div>
        <footer className="flex justify-end gap-2 border-t border-zinc-800 p-4">
          <button onClick={onCancel} className="secondary-button" disabled={busy}>
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={busy}
            className="primary-button bg-red-600 hover:bg-red-500"
          >
            {busy ? '处理中...' : confirmLabel}
          </button>
        </footer>
      </div>
    </div>
  )
}
