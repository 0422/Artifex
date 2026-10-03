import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

/**
 * 2026-10-02 第三批：统一空状态组件。
 *
 * 原来各页空状态各自手写（一个大图标 + 一两行字），样式漂移且没有情感设计。
 * 统一为「图标置于双层光晕圆环中 + 标题 + 说明 + 可选操作」的结构：
 * 外环 1px zinc-800 勾轮廓，内层 teal/10 模糊光晕给一点品牌温度，
 * 图标用 zinc-500（非文本元素，3:1 对比度即达标）。
 */

export default function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="mx-auto flex max-w-sm flex-col items-center py-20 text-center">
      <span className="relative flex h-16 w-16 items-center justify-center">
        <span className="absolute inset-0 rounded-full ring-1 ring-inset ring-zinc-800" />
        <span className="absolute inset-3 rounded-full bg-teal-500/10 blur-[8px]" />
        <Icon className="relative text-zinc-500" size={26} strokeWidth={1.5} />
      </span>
      <h2 className="mt-5 font-medium text-zinc-200">{title}</h2>
      {description && <p className="mt-2 text-sm leading-6 text-zinc-400">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
