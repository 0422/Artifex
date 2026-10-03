import { AlertTriangle } from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'

import { useDialogExit } from '../lib/useDialogExit'

/**
 * 2026-09-30 删除确认弹窗。
 *
 * 知识与雅思题库的删除都是"软删除"（后端置 is_active=False），数据不会真丢，
 * 但界面上即刻消失且目前没有恢复入口，所以破坏性操作一律先确认。
 *
 * 2026-10-02 第二批：迁移到 Radix Dialog（Esc/焦点陷阱/遮罩关闭/滚动锁/进出场动画）。
 * 打开时 Radix 会把焦点给第一个可聚焦元素，即「取消」——破坏性操作不该被默认选中。
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
  // 2026-10-02 收尾轮：关闭走 useDialogExit（取消/Esc/遮罩都有退场动画）。
  // 确认删除也走 close()：动作立即执行，最坏情况（接口比退场动画快）就是原来的瞬时关闭，
  // 不存在回退
  const { open, close } = useDialogExit(onCancel)
  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) close() }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[70] bg-black/70 data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
        <Dialog.Content className="fixed inset-0 z-[70] flex items-center justify-center p-4 data-[state=open]:animate-dialog-in data-[state=closed]:animate-dialog-out">
          <div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl">
            <header className="flex items-center gap-2 border-b border-zinc-800 p-4">
              <AlertTriangle className="text-amber-400" size={18} />
              <Dialog.Title className="font-semibold">{title}</Dialog.Title>
            </header>
            <div className="space-y-3 p-5">
              <Dialog.Description asChild>
                <p className="whitespace-pre-wrap text-sm leading-6 text-zinc-300">{message}</p>
              </Dialog.Description>
              <p className="text-xs leading-5 text-zinc-400">
                删除后该内容将不再显示，官方题库不可删除。如需找回，请联系开发者直接改库。
              </p>
            </div>
            <footer className="flex justify-end gap-2 border-t border-zinc-800 p-4">
              <button onClick={close} className="secondary-button" disabled={busy}>
                取消
              </button>
              <button
                onClick={() => { close(); onConfirm() }}
                disabled={busy}
                /* 2026-10-02 删除按钮补齐 text-white：组件类收进 @layer components 后 bg-red-600 已能生效，
                   而 .primary-button 的深字（text-zinc-950）用在红底上对比度仅约 2:1，显式指定白字（约 4.9:1 达 AA） */
                className="primary-button bg-red-600 text-white hover:bg-red-500"
              >
                {busy ? '处理中...' : confirmLabel}
              </button>
            </footer>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
