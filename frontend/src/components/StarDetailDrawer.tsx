import { useEffect, useRef, useState } from 'react'
import { Archive, Copy, Pencil, Pin, RotateCcw, Sparkles, Star, Trash2, X } from 'lucide-react'
import { format } from 'date-fns'

import type { Star as StarModel, StarUpdate } from '../lib/types'
import { STAR_SOURCE_LABELS } from '../lib/types'
import { toast } from '../stores/toastStore'

// 2026-10-03 新增摘星阁（M7）抓星抽屉。
//
// 「抓」这个动词必须被看见：抽屉不是从右边滑出来，而是从被点那颗星的位置
// 放大飞到 final 位（FLIP）。约 25 行代码换一个动作的全部身体感，值得。
// reduced-motion 下直接跳过，退化为淡入。
//
// 抽屉永远渲染在 DOM 里（无选中时显示引导语），好处是 xl 断点下并排布局稳定，
// 不会因为打开/关闭而让夜空区抖动。

export interface StarDetailDrawerProps {
  /** 1 颗 = 从夜空抓的；3 颗 = 伸手抓一把。为空表示还没抓过任何星 */
  stars: StarModel[]
  /** 正在按 id 拉详情：抽屉先出骨架，别让夜空区的能力等网络 */
  pendingId: string | null
  /** 被点那颗星的视口矩形，FLIP 的起点。伸手抓一把时为 null（不飞） */
  originRect: DOMRect | null
  onClose: () => void
  onEdit: (star: StarModel) => void
  onDelete: (star: StarModel) => void
  onPatch: (star: StarModel, patch: StarUpdate) => void
}

function relativeTime(iso: string): string {
  return format(new Date(iso), 'yyyy-MM-dd HH:mm')
}

export default function StarDetailDrawer({
  stars,
  pendingId,
  originRect,
  onClose,
  onEdit,
  onDelete,
  onPatch,
}: StarDetailDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const [flip, setFlip] = useState<{ dx: number; dy: number; scale: number } | null>(null)
  // 只有第一颗星参与 FLIP：一次抓取 animation 只该有一个主角
  const flipKey = stars[0]?.id ?? null
  const drawerStarsEmpty = stars.length === 0

  useEffect(() => {
    if (!originRect || !flipKey) {
      setFlip(null)
      return
    }
    const panel = panelRef.current
    if (!panel) return
    // 障害用户不玩飞行：抽屉直接到位
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setFlip(null)
      return
    }
    const box = panel.getBoundingClientRect()
    const dx = originRect.left + originRect.width / 2 - (box.left + box.width / 2)
    const dy = originRect.top + originRect.height / 2 - (box.top + box.height / 2)
    // 星点本身只有 3-5px，按真实比例算会缩到看不见；
    // 放大 4 倍并夹在 0.14-0.5 之间，读起来是"一颗光点绽开成一面星图"
    const scale = Math.max(0.14, Math.min(0.5, (originRect.width / Math.max(box.width, 1)) * 4))
    setFlip({ dx, dy, scale })
    // 下一帧再清掉 transform，浏览器才会去补那 260ms 的过渡
    const frame = requestAnimationFrame(() => setFlip(null))
    return () => cancelAnimationFrame(frame)
  }, [flipKey, originRect])

  const transform = flip
    ? `translate(${flip.dx}px, ${flip.dy}px) scale(${flip.scale})`
    : 'translate(0, 0) scale(1)'

  // 没抓任何星时，小屏上整个抽屉退场（不该有一块空面板盖住夜空）；
  // xl 断点保留，并排布局下它常驻且显示引导语
  const idle = drawerStarsEmpty && pendingId === null

  return (
    <aside
      className={`panel fixed inset-y-1.5 right-1.5 z-40 w-[calc(100%-0.75rem)] max-w-md flex-col xl:static xl:flex xl:w-96 xl:shrink-0 ${
        idle ? 'hidden' : 'flex'
      }`}
    >
      <div
        ref={panelRef}
        style={{ transform }}
        className={`flex h-full min-h-0 flex-col overflow-hidden rounded-lg transition-[transform,opacity] duration-[260ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${
          flip ? 'opacity-40' : 'opacity-100'
        }`}
      >
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-zinc-800 px-4">
          <Sparkles size={15} className="text-teal-400" />
          <h2 className="text-sm font-semibold text-zinc-100">
            {stars.length > 1 ? `一把星 · ${stars.length}` : '星体'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            title="放回夜空（Esc）"
            aria-label="放回夜空"
            className="icon-button ml-auto h-7 w-7"
          >
            <X size={15} />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
          {pendingId !== null && stars.length === 0 && <StarSkeleton />}

          {pendingId === null && stars.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center px-4 text-center">
              <span className="relative flex h-14 w-14 items-center justify-center">
                <span className="absolute inset-0 rounded-full ring-1 ring-inset ring-zinc-800" />
                <span className="absolute inset-3 rounded-full bg-teal-500/10 blur-[8px]" />
                <Star className="relative text-zinc-500" size={20} strokeWidth={1.5} />
              </span>
              <p className="mt-4 text-sm text-zinc-300">夜空中还空着</p>
              <p className="mt-1.5 text-xs leading-5 text-zinc-400">
                点任意一颗星就能读它的内容。
                <br />
                也可以按 <kbd className="rounded border border-zinc-700 px-1 text-[10px]">N</kbd> 写下新的一念，
                按 <kbd className="rounded border border-zinc-700 px-1 text-[10px]">R</kbd> 伸手随机抓一把。
              </p>
            </div>
          )}

          {stars.map((star) => (
            <StarCard
              key={star.id}
              star={star}
              compact={stars.length > 1}
              onEdit={() => onEdit(star)}
              onDelete={() => onDelete(star)}
              onPatch={(patch) => onPatch(star, patch)}
            />
          ))}
        </div>
      </div>
    </aside>
  )
}

function StarCard({
  star,
  compact,
  onEdit,
  onDelete,
  onPatch,
}: {
  star: StarModel
  compact: boolean
  onEdit: () => void
  onDelete: () => void
  onPatch: (patch: StarUpdate) => void
}) {
  const edited = new Date(star.updated_at).getTime() - new Date(star.created_at).getTime() > 2000
  return (
    <article className="panel bg-zinc-950/60 p-4">
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
        <span className="rounded-md border border-teal-800 bg-teal-950 px-1.5 py-0.5 text-teal-300">
          {STAR_SOURCE_LABELS[star.source]}
        </span>
        <span title={relativeTime(star.created_at)}>落于 {relativeTime(star.created_at)}</span>
        {edited && <span className="text-zinc-600">· 改于 {relativeTime(star.updated_at)}</span>}
        {/* 归档态要在卡片上直接说出来：抽屉不会因为归档而关掉，
            用户视角里"我刚点的按钮有反馈吗"全靠这一行 */}
        {star.is_archived && (
          <span className="rounded-md border border-zinc-600 bg-zinc-800 px-1.5 py-0.5 text-zinc-300">
            已归档
          </span>
        )}
      </div>

      <p
        className={`mt-3 whitespace-pre-wrap break-words text-zinc-100 ${
          compact ? 'text-xs leading-6' : 'text-sm leading-7'
        }`}
      >
        {star.content}
      </p>

      {star.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {star.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-md border border-zinc-700 bg-zinc-800 px-1.5 py-0.5 text-[11px] text-zinc-400"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {!compact && (
        <div className="mt-4 flex items-center gap-1 border-t border-zinc-800 pt-3">
          <button
            type="button"
            title={star.is_favorite ? '取消收藏' : '收藏'}
            aria-label={star.is_favorite ? '取消收藏' : '收藏'}
            onClick={() => onPatch({ is_favorite: !star.is_favorite })}
            className={`icon-button h-8 w-8 ${star.is_favorite ? 'text-amber-300' : ''}`}
          >
            <Star size={15} fill={star.is_favorite ? 'currentColor' : 'none'} />
          </button>
          <button
            type="button"
            title={star.is_pinned ? '取消钉住' : '钉在夜空顶端'}
            aria-label={star.is_pinned ? '取消钉住' : '钉在夜空顶端'}
            onClick={() => onPatch({ is_pinned: !star.is_pinned })}
            className={`icon-button h-8 w-8 ${star.is_pinned ? 'text-amber-400' : ''}`}
          >
            <Pin size={15} />
          </button>
          <button
            type="button"
            title="复制全文"
            aria-label="复制全文"
            onClick={() => {
              // clipboard 在非安全上下文（http、部分内网环境）下根本不存在，
              // 直接静默失败用户会以为按钮是坏的
              if (!navigator.clipboard) {
                toast.error('当前环境不支持一键复制，请手动选中全文')
                return
              }
              navigator.clipboard
                .writeText(star.content)
                .then(() => toast.ok('已复制到剪贴板'))
                .catch(() => toast.error('复制失败，请手动选中'))
            }}
            className="icon-button h-8 w-8"
          >
            <Copy size={15} />
          </button>
          <button
            type="button"
            title={star.is_archived ? '放回夜空' : '归档（流星划过，之后在「归档」里还能找回）'}
            aria-label={star.is_archived ? '放回夜空' : '归档'}
            onClick={() => onPatch({ is_archived: !star.is_archived })}
            className={`icon-button h-8 w-8 ${star.is_archived ? 'text-teal-300' : ''}`}
          >
            {star.is_archived ? <RotateCcw size={15} /> : <Archive size={15} />}
          </button>
          <button type="button" title="编辑" aria-label="编辑" onClick={onEdit} className="icon-button h-8 w-8">
            <Pencil size={15} />
          </button>
          <button
            type="button"
            title="删除"
            aria-label="删除"
            onClick={onDelete}
            className="icon-button ml-auto h-8 w-8 hover:text-red-300"
          >
            <Trash2 size={15} />
          </button>
        </div>
      )}
    </article>
  )
}

function StarSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="正在抓住这颗星">
      <div className="skeleton h-5 w-20" />
      <div className="skeleton h-4 w-full" />
      <div className="skeleton h-4 w-11/12" />
      <div className="skeleton h-4 w-4/5" />
      <div className="skeleton h-4 w-2/3" />
      <div className="skeleton mt-4 h-8 w-full" />
    </div>
  )
}
