import { create } from 'zustand'

/**
 * 2026-10-02 全局 toast 队列。
 *
 * 从边缘设备页的下发反馈场景孵化：推送 OTA/配置要好几秒，用户常切走标签页，
 * 原来贴在 tab 里的内联文字一切走就看不见结果了。toast 挂右上角常驻不丢。
 * 点击与定时都会触发同一套 dismiss，退出动画由组件层负责。
 */

export type ToastKind = 'ok' | 'error'

export interface ToastItem {
  id: number
  kind: ToastKind
  text: string
}

interface ToastState {
  toasts: ToastItem[]
  push: (kind: ToastKind, text: string) => number
  dismiss: (id: number) => void
}

let seq = 0

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (kind, text) => {
    seq += 1
    const id = seq
    set((state) => ({ toasts: [...state.toasts, { id, kind, text }] }))
    return id
  },
  dismiss: (id) => set((state) => ({ toasts: state.toasts.filter((item) => item.id !== id) })),
}))

/** 非组件上下文（service 回调、普通函数）里直接调这个 */
export const toast = {
  ok: (text: string) => useToastStore.getState().push('ok', text),
  error: (text: string) => useToastStore.getState().push('error', text),
}
