import { Info } from 'lucide-react'

/**
 * 2026-09-30 只读提示弹窗。
 *
 * 官方共享分类/真题右键能弹出菜单（保持操作入口一致），
 * 但点「删除」时用这个弹窗说明不可删除，而不是静默无响应。
 */
export default function InfoDialog({
  title,
  message,
  onClose,
}: {
  title: string
  message: string
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-[75] grid place-items-center bg-black/70 p-4">
      <div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl">
        <header className="flex items-center gap-2 border-b border-zinc-800 p-4">
          <Info className="text-teal-400" size={18} />
          <h2 className="font-semibold">{title}</h2>
        </header>
        <div className="p-5">
          <p className="whitespace-pre-wrap text-sm leading-6 text-zinc-300">{message}</p>
        </div>
        <footer className="flex justify-end border-t border-zinc-800 p-4">
          <button onClick={onClose} className="primary-button">知道了</button>
        </footer>
      </div>
    </div>
  )
}
