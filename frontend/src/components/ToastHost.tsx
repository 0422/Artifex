import { useEffect, useState } from 'react'
import { CheckCircle2, X, XCircle } from 'lucide-react'

import { useToastStore, type ToastItem } from '../stores/toastStore'

/** 自动消失时长；错误多留 1.5s，毕竟要读 */
const DURATION: Record<ToastItem['kind'], number> = { ok: 3200, error: 4800 }
/** 退场动画时长，需与 index.css 的 animate-toast-out 保持一致 */
const EXIT_MS = 180

export default function ToastHost() {
  const toasts = useToastStore((s) => s.toasts)

  return (
    // pointer-events-none 让堆叠区不挡操作，具体每条 toast 再单独打开事件
    <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-80 flex-col gap-2" role="region" aria-label="通知">
      {toasts.map((item) => <ToastCard key={item.id} item={item} />)}
    </div>
  )
}

function ToastCard({ item }: { item: ToastItem }) {
  const dismiss = useToastStore((s) => s.dismiss)
  const [closing, setClosing] = useState(false)

  const close = () => {
    if (closing) return
    setClosing(true)
    // 等退场动画播完再从队列移除；reduced-motion 下动画被压到 0.01ms，这里的延时依然成立
    window.setTimeout(() => dismiss(item.id), EXIT_MS)
  }

  useEffect(() => {
    const timer = window.setTimeout(close, DURATION[item.kind])
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const isOk = item.kind === 'ok'
  return (
    <div
      // role=status 自带 aria-live=polite，屏幕阅读器会播报
      role="status"
      className={`pointer-events-auto flex items-start gap-2.5 rounded-lg border px-3.5 py-3 shadow-float backdrop-blur-sm ${
        isOk ? 'border-emerald-800/80 bg-emerald-950/90 text-emerald-200' : 'border-red-800/80 bg-red-950/90 text-red-200'
      } ${closing ? 'animate-toast-out' : 'animate-toast-in'}`}
    >
      {isOk ? <CheckCircle2 size={16} className="mt-px shrink-0" /> : <XCircle size={16} className="mt-px shrink-0" />}
      <p className="min-w-0 flex-1 text-xs leading-5">{item.text}</p>
      <button type="button" onClick={close} aria-label="关闭通知" className="-m-0.5 shrink-0 rounded p-0.5 opacity-60 transition-opacity hover:opacity-100">
        <X size={13} />
      </button>
    </div>
  )
}
