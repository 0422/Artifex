import { Info } from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'

import { useDialogExit } from '../lib/useDialogExit'

/**
 * 2026-09-30 只读提示弹窗。
 *
 * 官方共享分类/真题右键能弹出菜单（保持操作入口一致），
 * 但点「删除」时用这个弹窗说明不可删除，而不是静默无响应。
 *
 * 2026-10-02 第二批：迁移到 Radix Dialog。原先是手写 div —— 无 Esc、无焦点陷阱、
 * 不锁背景滚动，也没有进出场动画。Radix 一并补齐（aria 属性/焦点归还/滚动锁），
 * 进出场由 data-[state] 驱动 index.css 里的 animate-dialog-in/out。
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
  // 2026-10-02 收尾轮：关闭走 useDialogExit，先播退场动画再卸载
  const { open, close } = useDialogExit(onClose)
  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) close() }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[75] bg-black/70 data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
        <Dialog.Content className="fixed inset-0 z-[75] flex items-center justify-center p-4 data-[state=open]:animate-dialog-in data-[state=closed]:animate-dialog-out">
          <div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl">
            <header className="flex items-center gap-2 border-b border-zinc-800 p-4">
              <Info className="text-teal-400" size={18} />
              <Dialog.Title className="font-semibold">{title}</Dialog.Title>
            </header>
            <div className="p-5">
              <Dialog.Description asChild>
                <p className="whitespace-pre-wrap text-sm leading-6 text-zinc-300">{message}</p>
              </Dialog.Description>
            </div>
            <footer className="flex justify-end border-t border-zinc-800 p-4">
              <button onClick={close} className="primary-button">知道了</button>
            </footer>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
