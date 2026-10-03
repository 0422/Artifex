import { useCallback, useRef, useState } from 'react'

/**
 * 2026-10-02 收尾轮：让 Radix Dialog 播上退场动画的小钩子。
 *
 * 背景：各弹窗都是父组件条件渲染（{x && <Dialog/>}），关闭时父组件直接卸载，
 * Radix 的退场动画（data-[state=closed]:animate-dialog-out 等）来不及播，
 * 表现为"啪"地消失。
 *
 * 用法（以 InfoDialog 为例）：
 *   const { open, close } = useDialogExit(onClose)
 *   <Dialog.Root open={open} onOpenChange={(o) => { if (!o) close() }}>
 * 所有关闭入口（右上角 X、取消按钮）都调 close() 而不是直接 onClose()：
 * close() 先把 open 置 false，Radix 据此播完退场（150~180ms），
 * 再回调父级真正卸载组件。EXIT_MS 取 200ms，长于最慢的 slide-out-right。
 *
 * 注意：hook 本身必须在组件顶层无条件调用；如果弹窗渲染在 {cond && ...}
 * 条件块里（如 ScenarioManager 的编辑弹窗），把 hook 提到组件顶部即可，
 * close 回调在条件块内使用。
 */

/** 退场动画时长上限 + 20ms 余量，确保最长的一条（slide-out-right 0.18s）播完 */
const EXIT_MS = 200

export function useDialogExit(onClose: () => void) {
  const [open, setOpen] = useState(true)
  // 用 ref 持有最新 onClose：close 的 useCallback 不必因父组件重渲染而重建，
  // 也不会捕获到旧的闭包（与 AccountMenu 里 closeRef 同一手法）
  const closeRef = useRef(onClose)
  closeRef.current = onClose

  const close = useCallback(() => {
    setOpen(false)
    window.setTimeout(() => closeRef.current(), EXIT_MS)
  }, [])

  //  reopen：仅"父组件常驻、弹窗条件渲染"的场景需要（如 ScenarioManager 的编辑弹窗——
  // hook 在组件顶层，弹窗 JSX 在 {editing && ...} 块里）。关闭后 open 停在 false，
  // 下次打开必须 reset 回 true，否则 Dialog.Root 会因 open=false 渲染不出内容。
  // 其余弹窗都是独立组件、随父级条件卸载重生，用不到这个
  const reopen = useCallback(() => setOpen(true), [])

  return { open, close, reopen }
}
