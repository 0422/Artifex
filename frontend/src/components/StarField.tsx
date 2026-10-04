import { useCallback, useMemo, useRef } from 'react'
import type { CSSProperties, KeyboardEvent } from 'react'
import { format } from 'date-fns'

import type { StarBrief } from '../lib/types'

// 2026-10-03 新增摘星阁（M7）星空画布：位置、闪烁、抓取三件事。
//
// 设计要点（详见 docs/design/phases/M7.md 第 9 节）：
//   1. 星体位置【只由 id 决定】，与筛选/分页/归档完全解耦。若按列表序号排布，
//      一筛选全部星换位，用户刚建立的空间记忆就毁了。
//   2. 闪烁是纯 CSS 动画（时长/相位由 id 哈希派生），不跑 rAF 循环，
//      200 颗星的主线程开销为零。
//   3. 长文星的判定用 preview 是否以省略号结尾——后端 preview 截断到 80 字，
//      尾巴上是"…"即代表"这颗里面还有更多"，不必为此加接口字段。

/** 星图可用区域：相对容器的百分比半径。横向略大于纵向，贴合桌面宽 panel */
const RX = 46
const RY = 43
/** 置顶星压到内圈的比例：用户亲手插上去的那几颗，理应第一个被看到 */
const PIN_RATIO = 0.45
/** 单次渲染上限。DOM 方案的舒适区，超出请改 Canvas（M7.md 9-2） */
export const MAX_RENDERED = 200

const ARROW_VECTORS: Record<string, [number, number]> = {
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
  ArrowUp: [0, -1],
  ArrowDown: [0, 1],
}

/** FNV-1a 32 位。UUID 字符串上分布足够均匀，且零依赖 */
function fnv1a(text: string): number {
  let hash = 0x811c9dc5
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index)
    hash = Math.imul(hash, 0x01000193)
  }
  return hash >>> 0
}

export type StarTier = 'short' | 'medium' | 'long'

export interface StarPlacement {
  id: string
  /** 归一化坐标，-1..1。转成百分比时乘 RX/RY */
  x: number
  y: number
  tier: StarTier
  /** 闪烁周期（秒）与相位（秒，负值）。置顶/收藏星不闪烁，两者均为 0 */
  duration: number
  delay: number
}

/**
 * 由 id 推导一颗星在夜空中的位置与闪烁参数。纯函数，同样输入永远同样输出。
 *
 * 半径用 sqrt(t) 而非 t：t 均匀分布在 [0,1) 时，sqrt(t) 在圆盘上才是均匀的
 * （否则星会明显向圆心聚集，外圈稀稀拉拉）。
 */
export function placeStar(id: string, preview: string, isPinned: boolean): StarPlacement {
  const h1 = fnv1a(id)
  const h2 = fnv1a(`${id}:twinkle`)
  const t = (h1 >>> 8) / 0xffffff
  const angle = ((h2 >>> 0) / 0x100000000) * Math.PI * 2
  const radius = Math.sqrt(t) * (isPinned ? PIN_RATIO : 1)
  // preview 以省略号结尾 = 后端截过断 = 正文超过 80 字，渲染成大一点的光斑
  const truncated = preview.endsWith('…')
  const tier: StarTier = truncated ? 'long' : preview.length <= 30 ? 'short' : 'medium'
  return {
    id,
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
    tier,
    duration: isPinned ? 0 : 2.6 + (h2 % 24) / 10,
    delay: isPinned ? 0 : -((h2 >>> 5) % 40) / 10,
  }
}

const TIER_SIZE: Record<StarTier, number> = { short: 3, medium: 4, long: 5 }

/**
 * 方向键找下一颗星：在按下方向上的投影必须为正（只往前找），
 * 用「前进量 + 横向偏移惩罚」打分取最小。横向惩罚系数 2.2 让
 * 按右键时优先选同一行的星，而不是斜对面那颗。
 */
function findNearest(
  placements: StarPlacement[],
  from: StarPlacement,
  vector: [number, number],
): StarPlacement | undefined {
  let best: StarPlacement | undefined
  let bestScore = Number.POSITIVE_INFINITY
  for (const candidate of placements) {
    if (candidate.id === from.id) continue
    const dx = candidate.x - from.x
    const dy = candidate.y - from.y
    const along = dx * vector[0] + dy * vector[1]
    if (along <= 0.001) continue
    const across = Math.abs(dx * vector[1] - dy * vector[0])
    const score = along + across * 2.2
    if (score < bestScore) {
      bestScore = score
      best = candidate
    }
  }
  return best
}

function starAriaLabel(star: StarBrief, index: number): string {
  const parts = [`第 ${index + 1} 颗星`, star.preview, `捕获于 ${format(new Date(star.created_at), 'yyyy-MM-dd HH:mm')}`]
  if (star.tags.length > 0) parts.push(`标签 ${star.tags.join('、')}`)
  if (star.is_pinned) parts.push('已钉住')
  if (star.is_favorite) parts.push('已收藏')
  return parts.join('，')
}

/** 阁楼剪影：屋檐 + 栏杆。淡到"第二眼才发现"的程度，只为把"站在高处"立起来 */
function PavilionRail() {
  return (
    <svg
      viewBox="0 0 1200 72"
      preserveAspectRatio="none"
      aria-hidden="true"
      className="pointer-events-none absolute inset-x-0 bottom-0 h-10 w-full text-zinc-900"
    >
      {/* 阑干横木 */}
      <rect x="0" y="8" width="1200" height="4" fill="currentColor" opacity="0.9" />
      {/* 立柱 */}
      {Array.from({ length: 16 }, (_, index) => (
        <rect key={index} x={28 + index * 74} y="12" width="3" height="52" fill="currentColor" opacity="0.75" />
      ))}
      {/* 屋檐：更高更暗的一道，暗示头顶有遮蔽 */}
      <rect x="0" y="0" width="1200" height="5" fill="currentColor" />
    </svg>
  )
}

export interface StarFieldProps {
  stars: StarBrief[]
  /** 夜空中的总数（可能远大于已渲染数），用于如实告知 */
  total: number
  loading: boolean
  /** 已抓过（打开过详情）的星 id，用于显示"已读"细环 */
  grabbedIds: ReadonlySet<string>
  /** 当前生效的标签筛选。非空时同标签的星会被连成星座 */
  activeTag: string | null
  selectedId: string | null
  hasMore: boolean
  onGrab: (star: StarBrief, rect: DOMRect) => void
  onLoadMore: () => void
}

export default function StarField({
  stars,
  total,
  loading,
  grabbedIds,
  activeTag,
  selectedId,
  hasMore,
  onGrab,
  onLoadMore,
}: StarFieldProps) {
  const buttonsRef = useRef(new Map<string, HTMLButtonElement>())

  const placements = useMemo(
    // 防御性截断：调用方多给了也只在夜空中画 MAX_RENDERED 颗，
    // 与底部"当前视野 N 颗"的告知口径保持一致
    () => stars.slice(0, MAX_RENDERED).map((star) => placeStar(star.id, star.preview, star.is_pinned)),
    [stars],
  )

  // React 19 的 ref 回调可以返回清理函数，元素卸载时自动把索引删掉
  const registerButton = useCallback((element: HTMLButtonElement | null) => {
    const map = buttonsRef.current
    if (element === null) return
    const id = element.dataset.starId ?? ''
    map.set(id, element)
    return () => {
      map.delete(id)
    }
  }, [])

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      const vector = ARROW_VECTORS[event.key]
      if (!vector) return
      const active = document.activeElement
      const fromId = active instanceof HTMLElement ? active.dataset.starId : undefined
      const from = fromId ? placements.find((placement) => placement.id === fromId) : undefined
      if (!from) return
      event.preventDefault()
      const next = findNearest(placements, from, vector)
      if (next) buttonsRef.current.get(next.id)?.focus()
    },
    [placements],
  )

  const constellation = useMemo(() => {
    if (!activeTag || placements.length < 2 || placements.length > 40) return null
    // 按极角排序后首尾相连，得到的是一条闭合折线而不是一团交叉线
    return [...placements].sort((a, b) => Math.atan2(a.y, a.x) - Math.atan2(b.y, b.x))
  }, [activeTag, placements])

  return (
    <div
      role="group"
      aria-label="星空"
      onKeyDown={handleKeyDown}
      className="relative min-h-[22rem] flex-1 overflow-hidden"
      style={{
        // 地平线方向微微泛青：暗示"阁楼下方有光"，同时让整块夜空不与 zinc-950 底色脱开
        background:
          'radial-gradient(120% 70% at 50% 118%, rgba(19,78,74,0.42), transparent 62%), radial-gradient(80% 50% at 78% -10%, rgba(30,41,59,0.55), transparent 70%)',
      }}
    >
      {constellation && (
        <svg
          aria-hidden="true"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="pointer-events-none absolute inset-0 h-full w-full text-zinc-600"
        >
          {constellation.map((placement, index) => {
            const next = constellation[(index + 1) % constellation.length]
            return (
              <line
                key={placement.id}
                x1={50 + placement.x * RX}
                y1={50 + placement.y * RY}
                x2={50 + next.x * RX}
                y2={50 + next.y * RY}
                stroke="currentColor"
                strokeWidth={0.14}
                opacity={0.5}
              />
            )
          })}
        </svg>
      )}

      {loading ? (
        <SkySkeleton />
      ) : (
        placements.map((placement, index) => {
          const star = stars[index]
          const dimmed = activeTag !== null && !star.tags.includes(activeTag)
          const size = TIER_SIZE[placement.tier]
          const steady = star.is_pinned || star.is_favorite
          const selected = star.id === selectedId
          // 光环优先级：钉住 > 收藏 > 长文 > 已抓。一颗星只套一圈，
          // 圈叠圈会变成毛线球，也读不出主状态。
          const halo = star.is_pinned
            ? 'border-amber-400/40'
            : star.is_favorite
              ? 'border-amber-300/40'
              : placement.tier === 'long'
                ? 'border-teal-300/45'
                : grabbedIds.has(star.id)
                  ? 'border-teal-500/45'
                  : null
          const dotClass = star.is_pinned
            ? 'bg-amber-400 shadow-[0_0_9px_2px_rgba(251,191,36,0.4)]'
            : star.is_favorite
              ? 'bg-amber-300 shadow-[0_0_7px_2px_rgba(252,211,77,0.32)]'
              : 'bg-teal-200 shadow-[0_0_7px_1px_rgba(153,246,228,0.32)]'

          return (
            <button
              key={star.id}
              ref={registerButton}
              data-star-id={star.id}
              type="button"
              aria-label={starAriaLabel(star, index)}
              aria-current={selected || undefined}
              onClick={(event) => onGrab(star, event.currentTarget.getBoundingClientRect())}
              style={
                {
                  left: `${50 + placement.x * RX}%`,
                  top: `${50 + placement.y * RY}%`,
                } as CSSProperties
              }
              className={`group absolute flex h-6 w-6 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full transition-[transform,opacity] duration-150 hover:scale-[1.6] hover:opacity-100 focus-visible:scale-[1.6] active:scale-125 ${
                dimmed ? 'opacity-20' : ''
              } ${selected ? 'scale-[1.6]' : ''}`}
            >
              {halo && <span className={`absolute h-3.5 w-3.5 rounded-full border ${halo}`} />}
              <span
                className={`block rounded-full animate-twinkle ${dotClass}`}
                style={{
                  width: size,
                  height: size,
                  animationDuration: steady ? undefined : `${placement.duration}s`,
                  animationDelay: steady ? undefined : `${placement.delay}s`,
                  // 变暗时闪烁也停住：一片静止的暗点比一堆乱眨的暗点安静得多
                  animationPlayState: dimmed ? 'paused' : undefined,
                }}
              />
              {/* 悬停/聚焦时浮出预览。贴右缘时翻到左侧，避免 tooltip 探出夜空被裁掉 */}
              <span
                className={`pointer-events-none absolute top-1/2 z-20 block w-52 -translate-y-1/2 rounded-md border border-zinc-700 bg-zinc-900/95 px-2.5 py-2 text-left opacity-0 shadow-float backdrop-blur transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 ${
                  placement.x > 0.35 ? 'right-full mr-2' : 'left-full ml-2'
                }`}
              >
                <span className="block text-[11px] leading-4 text-zinc-300">{star.preview}</span>
                <span className="mt-1 block text-[10px] text-zinc-500">
                  {format(new Date(star.created_at), 'MM-dd HH:mm')}
                  {star.tags.length > 0 && ` · ${star.tags.slice(0, 3).join(' / ')}`}
                </span>
              </span>
            </button>
          )
        })
      )}

      <PavilionRail />

      {/* 视野边界必须说出来：静默截断会被用户当成"数据丢了"。
          加载中不显示——此刻总数还没回来，报个 0/0 只会让人以为星空是空的 */}
      {!loading && (
        <div className="absolute inset-x-0 bottom-11 flex items-center justify-center gap-3 text-[11px] text-zinc-500">
          <span>
            夜空中 {total} 颗 · 当前视野 {placements.length} 颗
          </span>
          {hasMore && (
            <button
              type="button"
              onClick={onLoadMore}
              className="rounded-md border border-zinc-700 bg-zinc-950/80 px-2 py-0.5 text-[11px] text-zinc-300 transition-colors hover:border-teal-600 hover:text-teal-300"
            >
              再望远处一些
            </button>
          )}
        </div>
      )}
    </div>
  )
}

/** 加载态：12 个随机位置的闪烁小点。比灰块骨架贴题，成本也更低 */
function SkySkeleton() {
  const dots = useMemo(
    () =>
      Array.from({ length: 12 }, (_, index) => {
        const placement = placeStar(`skeleton-${index}`, '', false)
        return { ...placement, duration: 2.6 + index * 0.15, delay: -index * 0.3 }
      }),
    [],
  )
  return (
    <div aria-busy="true" aria-label="正在点亮星空">
      {dots.map((dot) => (
        <span
          key={dot.id}
          className="absolute h-1 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-zinc-600 animate-twinkle"
          style={{
            left: `${50 + dot.x * RX}%`,
            top: `${50 + dot.y * RY}%`,
            animationDuration: `${dot.duration}s`,
            animationDelay: `${dot.delay}s`,
          }}
        />
      ))}
    </div>
  )
}
