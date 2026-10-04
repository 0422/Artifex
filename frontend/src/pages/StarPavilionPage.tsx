import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Archive, Download, FileJson, Hand, List, LayoutGrid, Moon, Pencil, Pin, RotateCcw, Search, Sparkles, Star, X } from 'lucide-react'

import ConfirmDialog from '../components/ConfirmDialog'
import EmptyState from '../components/EmptyState'
import StarDetailDrawer from '../components/StarDetailDrawer'
import StarEditorDialog from '../components/StarEditorDialog'
import StarField, { MAX_RENDERED } from '../components/StarField'
import StarImportDialog from '../components/StarImportDialog'
import { starApi } from '../services/api'
import { toast } from '../stores/toastStore'
import {
  STAR_RANGE_LABELS,
  type Star as StarModel,
  type StarBrief,
  type StarImportInput,
  type StarInput,
  type StarRange,
  type StarSort,
  type StarTagCount,
  type StarUpdate,
} from '../lib/types'

// 2026-10-03 新增摘星阁（M7）主页面。
//
// 页面分四层：
//   ① 顶栏「写下这一念」输入框 —— 捕获入口，回车即收录
//   ② 筛选条 —— 时间范围 / 标签 / 收藏 / 钉住 / 归档 / 关键词
//   ③ 夜空 —— 星图模式与清单模式共用同一份数据，可随时互切
//   ④ 抓星抽屉 —— 常驻 DOM，xl 断点与夜空并排，小屏浮层
//
// 两条刻意的设计约束：
//   1. 视野边界必须说出来。夜空中 3000 颗 ≠ 画 3000 颗；单次最多 MAX_RENDERED，
//      底部常驻一行"夜空中 N 颗 · 当前视野 M 颗"，剩下的靠筛选/搜索/加载更多。
//      静默截断会被用户当成"数据丢了"。
//   2. 筛选一律即时生效并重置分页，不做"应用筛选"按钮——筛选是探索动作，
//      不是提交动作。

const RANGES: StarRange[] = ['all', 'today', 'week', 'month', 'earlier']

/** 快捷键里 1-5 对应的时间范围，与本数组同序 */
const RANGE_KEYS = ['1', '2', '3', '4', '5']

/**
 * 把一次局部更新合并到星上。逐键判断而不是直接展开：
 * Partial<StarInput> 里没带的键一旦被展开成 undefined，会把 content/tags 冲掉。
 */
function applyPatch(star: StarModel, patch: StarUpdate): StarModel {
  const next: StarModel = { ...star }
  if (patch.content !== undefined) next.content = patch.content
  if (patch.tags !== undefined) next.tags = patch.tags
  if (patch.is_pinned !== undefined) next.is_pinned = patch.is_pinned
  if (patch.is_favorite !== undefined) next.is_favorite = patch.is_favorite
  if (patch.is_archived !== undefined) next.is_archived = patch.is_archived
  return next
}

export default function StarPavilionPage() {
  const [view, setView] = useState<'sky' | 'list'>('sky')
  const [items, setItems] = useState<StarBrief[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [tag, setTag] = useState<string | null>(null)
  const [range, setRange] = useState<StarRange>('all')
  // 2026-10-03 「最常回味」排序（M7 第 7 节 #4）：按 last_grabbed_at 倒序，
  // 从没被抓过的星沉底。回答的是"我真正反复回头看的是哪些念头"
  const [sort, setSort] = useState<StarSort>('recent')
  const [favoriteOnly, setFavoriteOnly] = useState(false)
  const [pinnedOnly, setPinnedOnly] = useState(false)
  const [archivedView, setArchivedView] = useState(false)

  const [keywordInput, setKeywordInput] = useState('')
  const [keyword, setKeyword] = useState('')
  const [tagList, setTagList] = useState<StarTagCount[]>([])

  // 抽屉：stars 长度 1 = 从夜空抓的；3 = 伸手抓一把
  const [drawerStars, setDrawerStars] = useState<StarModel[]>([])
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [originRect, setOriginRect] = useState<DOMRect | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [grabbedIds, setGrabbedIds] = useState<ReadonlySet<string>>(() => new Set<string>())

  const [editorOpen, setEditorOpen] = useState(false)
  const [editing, setEditing] = useState<StarModel | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [deleting, setDeleting] = useState<StarModel | null>(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [draft, setDraft] = useState('')

  const searchRef = useRef<HTMLInputElement>(null)
  // 请求序号：连续改筛选或连点"再望远处一些"时，先发的请求可能后返回。
  // 不比对序号的话，过期响应会用旧 items/total/page 覆盖新状态，
  // append 分支还会把同一页重复追加进列表
  const requestIdRef = useRef(0)

  // ---------- 数据加载 ----------

  // 搜索防抖 250ms（与知识库搜索同一节奏）。设置 keywordInput 的人不该感受到延迟，
  // 但每敲一个字就打一次接口既浪费又会让夜空反复重排
  useEffect(() => {
    const timer = window.setTimeout(() => setKeyword(keywordInput.trim()), 250)
    return () => window.clearTimeout(timer)
  }, [keywordInput])

  const loadPage = useCallback(
    async (target: number, append: boolean) => {
      const requestId = requestIdRef.current + 1
      requestIdRef.current = requestId
      setLoading(true)
      try {
        const data = await starApi.list({
          tag: tag ?? undefined,
          range,
          sort,
          favorite: favoriteOnly,
          pinned: pinnedOnly,
          archived: archivedView,
          q: keyword || undefined,
          page: target,
        })
        // 期间又发了新请求（用户改了筛选）：这次结果直接丢掉的
        if (requestIdRef.current !== requestId) return
        setItems((prev) => (append ? [...prev, ...data.items] : data.items))
        setTotal(data.total)
        setPage(target)
        setError('')
      } catch {
        // 过期请求的失败不该把用户的错误条亮出来
        if (requestIdRef.current !== requestId) return
        setError('星星加载失败，请稍后重试')
      } finally {
        if (requestIdRef.current === requestId) setLoading(false)
      }
    },
    [tag, range, sort, favoriteOnly, pinnedOnly, archivedView, keyword],
  )

  // 任一筛选变化都回到第一页：分页与筛选混在一起会出现"第 3 页的今天"
  useEffect(() => {
    void loadPage(1, false)
  }, [loadPage])

  const loadTags = useCallback(async () => {
    try {
      setTagList(await starApi.tags())
    } catch {
      // 标签只影响筛选便捷度，取失败不该打扰用户，静默即可
    }
  }, [])

  useEffect(() => {
    void loadTags()
  }, [loadTags])

  const hasMore = items.length < total

  const loadMore = useCallback(() => {
    if (loading || !hasMore) return
    void loadPage(page + 1, true)
  }, [loading, hasMore, loadPage, page])

  // ---------- 抓取 ----------

  const grabStar = useCallback(async (star: StarBrief, rect: DOMRect) => {
    setOriginRect(rect)
    setSelectedId(star.id)
    setDrawerStars([])
    setPendingId(star.id)
    try {
      const detail = await starApi.detail(star.id)
      setDrawerStars([detail])
      setGrabbedIds((prev) => new Set(prev).add(star.id))
    } catch {
      toast.error('这颗星没抓住，请再点一次')
      setSelectedId(null)
    } finally {
      setPendingId(null)
    }
  }, [])

  const grabRandom = useCallback(async () => {
    setOriginRect(null)
    setSelectedId(null)
    try {
      const picked = await starApi.random({ count: 3 })
      if (picked.length === 0) {
        toast.error('夜空还空着，先写下一颗星吧')
        return
      }
      setDrawerStars(picked)
      setGrabbedIds((prev) => {
        const next = new Set(prev)
        for (const star of picked) next.add(star.id)
        return next
      })
    } catch {
      toast.error('抓了一把空手，稍后再试')
    }
  }, [])

  const closeDrawer = useCallback(() => {
    setDrawerStars([])
    setPendingId(null)
    setOriginRect(null)
    setSelectedId(null)
  }, [])

  // ---------- 增删改 ----------

  const createStar = useCallback(
    async (input: StarInput) => {
      await starApi.create(input)
      toast.ok('已收录一颗星')
      await Promise.all([loadPage(1, false), loadTags()])
    },
    [loadPage, loadTags],
  )

  const submitDraft = useCallback(async () => {
    const content = draft.trim()
    if (!content) return
    try {
      await createStar({ content })
      setDraft('')
    } catch {
      toast.error('收录失败，请稍后重试')
    }
  }, [createStar, draft])

  const patchStar = useCallback(
    async (star: StarModel, patch: StarUpdate) => {
      // 先落本地再发请求：收藏/钉住这种瞬时动作，等一个来回会让按钮像卡住了。
      // 逐键合并而不是 {...star, ...patch}：Partial 里没带的键会被展开成
      // undefined 覆盖掉（比如只传 is_favorite 时 content 会变成 undefined）。
      // 回滚要连 items 一起恢复——只恢复抽屉的话，失败后台列表里的置顶/收藏
      // 状态是错的，要等下一次加载才被人发现。
      const previousDrawer = drawerStars
      const previousItems = items
      const merged = applyPatch(star, patch)
      setDrawerStars((current) => current.map((item) => (item.id === star.id ? merged : item)))
      setItems((current) =>
        current.map((item) =>
          item.id === star.id
            ? {
                ...item,
                is_pinned: patch.is_pinned ?? item.is_pinned,
                is_favorite: patch.is_favorite ?? item.is_favorite,
              }
            : item,
        ),
      )
      try {
        const saved = await starApi.update(star.id, patch)
        setDrawerStars((current) => current.map((item) => (item.id === saved.id ? saved : item)))
        // 置顶改变排序、归档改变成员，列表都要重新取
        if (patch.is_pinned !== undefined || patch.is_archived !== undefined) {
          await loadPage(1, false)
        }
        if (patch.is_archived === true) toast.ok('这颗星划过夜空，已归档')
        if (patch.is_archived === false) toast.ok('这颗星回到了夜空')
      } catch {
        setDrawerStars(previousDrawer)
        setItems(previousItems)
        toast.error('操作失败，请稍后重试')
      }
    },
    [drawerStars, items, loadPage],
  )

  const removeStar = useCallback(async () => {
    if (deleting === null) return
    setDeleteBusy(true)
    try {
      await starApi.remove(deleting.id)
      setDrawerStars((current) => current.filter((item) => item.id !== deleting.id))
      setItems((current) => current.filter((item) => item.id !== deleting.id))
      setTotal((current) => Math.max(0, current - 1))
      toast.ok(`「${deleting.preview}」已从夜空中消失`)
      setDeleting(null)
    } catch {
      toast.error('删除失败，请稍后重试')
    } finally {
      setDeleteBusy(false)
    }
  }, [deleting])

  const importStars = useCallback(
    async (input: StarImportInput) => {
      const result = await starApi.importLines(input)
      toast.ok(`搬来了 ${result.created} 颗星${result.skipped > 0 ? `，跳过 ${result.skipped} 行` : ''}`)
      await Promise.all([loadPage(1, false), loadTags()])
      return result
    },
    [loadPage, loadTags],
  )

  // ---------- 键盘 ----------

  const anyDialogOpen = editorOpen || importOpen || deleting !== null
  const focusCapture = useCallback(() => {
    document.getElementById('star-capture')?.focus()
  }, [])
  // 弹窗开着时（编辑/导入/删除确认）整组快捷键让位：Radix 的焦点有时落在按钮上，
  // 不过 target 检查那一关，此时按 N 会再叠一个编辑弹窗出来
  const shortcutsEnabled = !anyDialogOpen

  useEffect(() => {
    if (!shortcutsEnabled) return
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      const target = event.target
      if (
        target instanceof HTMLElement &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
      ) {
        // 输入框里只放行 Esc（让输入框失焦），其余快捷键一律不抢——
        // 不然打一半字夜空突然重排是很恐怖的体验
        if (event.key === 'Escape') target.blur()
        return
      }
      if (event.metaKey || event.ctrlKey || event.altKey) return

      switch (event.key) {
        case 'Escape':
          closeDrawer()
          return
        case 'n':
        case 'N':
          event.preventDefault()
          setEditing(null)
          setEditorOpen(true)
          return
        case 'r':
        case 'R':
          event.preventDefault()
          void grabRandom()
          return
        case '/':
          event.preventDefault()
          searchRef.current?.focus()
          return
        default:
          break
      }
      const rangeIndex = RANGE_KEYS.indexOf(event.key)
      if (rangeIndex >= 0) {
        event.preventDefault()
        setRange(RANGES[rangeIndex])
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [shortcutsEnabled, closeDrawer, grabRandom])

  // ---------- 派生 ----------

  const filtered = useMemo(() => {
    // 后端已按置顶排序，这里再兜一层：刚在抽屉里钉住的星本地也要立刻冒到最前
    return [...items].sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned))
  }, [items])

  // 「全部清除」把夜空复位到默认视野，归档视图一并退出：
  // 归档是"位置"不是"筛选"，但它出现在同一排 chip 里，
  // 清完筛选却还停在归档态，只会让人以为清除失灵了
  const resetFilters = () => {
    setTag(null)
    setRange('all')
    setFavoriteOnly(false)
    setPinnedOnly(false)
    setArchivedView(false)
    setKeywordInput('')
  }

  // 「有筛选但没结果」与「夜空本来就有空」是两种完全不同的状态，
  // 前者该给"清除筛选"的出路，后者该给"写下第一颗"的邀请
  const filteredButEmpty =
    total === 0 &&
    !loading &&
    (keyword !== '' || tag !== null || range !== 'all' || favoriteOnly || pinnedOnly)

  // ---------- 渲染 ----------

  return (
    <div className="panel flex h-full min-h-0 flex-col overflow-hidden">
      <header className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-zinc-800 px-4 py-3 sm:px-5">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-lg font-semibold text-zinc-100">
            <Sparkles size={17} className="text-teal-400" />
            摘星阁
          </h1>
          <p className="mt-0.5 text-xs text-zinc-500">
            零零散散的语句与想法是一颗颗星星。站在阁楼上，抓住哪颗，就读哪颗。
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {/* 2026-10-03 数据导出（M7 第 7 节 #5）：整片夜空打包下载。
              两个格式分开而不是做一个下拉：Markdown 给人读，JSON 给将来搬去别处，
              这是两条不同的意图，藏进菜单里反而要多想一步 */}
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              void starApi
                .exportFile('md')
                .then(() => toast.ok('已导出 Markdown'))
                .catch(() => toast.error('导出失败，请稍后重试'))
            }}
          >
            <Download size={15} />
            导出 MD
          </button>
          <button
            type="button"
            className="icon-button"
            title="导出 JSON（机器可读，含标签/置顶/来源等全部元数据）"
            aria-label="导出 JSON"
            onClick={() => {
              void starApi
                .exportFile('json')
                .then(() => toast.ok('已导出 JSON'))
                .catch(() => toast.error('导出失败，请稍后重试'))
            }}
          >
            <FileJson size={15} />
          </button>
          <button type="button" className="secondary-button" onClick={() => setImportOpen(true)}>
            <Archive size={15} />
            搬一批过来
          </button>
        </div>
      </header>

      {/* ① 捕获入口：回车即收录，最短路径 */}
      <div className="shrink-0 px-4 pt-3 sm:px-5">
        <div className="panel flex items-center gap-2.5 bg-zinc-950 px-3 py-2">
          <Sparkles size={16} className="shrink-0 text-teal-400/80" />
          <input
            id="star-capture"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                void submitDraft()
              }
            }}
            placeholder="写下这一念 —— 回车收录，不用整理"
            className="min-w-0 flex-1 bg-transparent text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
          />
          {draft.length > 0 && (
            <button
              type="button"
              title="清空"
              aria-label="清空"
              onClick={() => setDraft('')}
              className="icon-button h-7 w-7"
            >
              <X size={14} />
            </button>
          )}
          {/* 快速路径归输入框（回车即收），完整路径归这支笔（多行 + 标签 + 收藏）。
              两个入口职责不同，不写成一个"写下一念"按钮让人猜 */}
          <button
            type="button"
            title="写长一点（多行、带标签）"
            aria-label="写长一点"
            onClick={() => {
              setEditing(null)
              setEditorOpen(true)
            }}
            className="icon-button h-7 w-7 shrink-0"
          >
            <Pencil size={14} />
          </button>
          <kbd className="hidden shrink-0 rounded border border-zinc-700 px-1.5 py-0.5 text-[10px] text-zinc-500 sm:block">
            ↵
          </kbd>
        </div>
      </div>

      {/* ② 筛选条 */}
      <div className="shrink-0 space-y-2 px-4 py-3 sm:px-5">
        <div className="flex flex-wrap items-center gap-1.5">
          {RANGES.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setRange(key)}
              className={`rounded-md border px-2.5 py-1 text-xs transition-colors ${
                range === key
                  ? 'border-teal-600 bg-teal-950 text-teal-300'
                  : 'border-zinc-700 bg-zinc-950 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {STAR_RANGE_LABELS[key]}
            </button>
          ))}

          <span className="mx-1 h-4 w-px bg-zinc-800" />

          {tagList.length === 0 ? (
            <span className="text-[11px] text-zinc-600">还没有标签</span>
          ) : (
            tagList.map((item) => (
              <button
                key={item.name}
                type="button"
                onClick={() => setTag((current) => (current === item.name ? null : item.name))}
                className={`rounded-md border px-2 py-1 text-[11px] transition-colors ${
                  tag === item.name
                    ? 'border-amber-600 bg-amber-950 text-amber-300'
                    : 'border-zinc-700 bg-zinc-950 text-zinc-400 hover:text-zinc-200'
                }`}
              >
                #{item.name}
                <span className="ml-1 text-zinc-600">{item.count}</span>
              </button>
            ))
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="flex h-8 min-w-40 flex-1 items-center gap-2 rounded-md border border-zinc-700 bg-zinc-950 px-2.5 sm:max-w-72">
            <Search size={14} className="shrink-0 text-zinc-500" />
            <input
              ref={searchRef}
              value={keywordInput}
              onChange={(event) => setKeywordInput(event.target.value)}
              placeholder="在星星里搜索（/）"
              className="min-w-0 flex-1 bg-transparent text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
            />
            {keywordInput && (
              <button
                type="button"
                aria-label="清空搜索"
                onClick={() => setKeywordInput('')}
                className="text-zinc-500 hover:text-zinc-200"
              >
                <X size={13} />
              </button>
            )}
          </label>

          <button
            type="button"
            onClick={() => setFavoriteOnly((value) => !value)}
            className={`flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs transition-colors ${
              favoriteOnly
                ? 'border-amber-600 bg-amber-950 text-amber-300'
                : 'border-zinc-700 bg-zinc-950 text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Star size={13} fill={favoriteOnly ? 'currentColor' : 'none'} />
            收藏
          </button>
          <button
            type="button"
            onClick={() => setPinnedOnly((value) => !value)}
            className={`flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs transition-colors ${
              pinnedOnly
                ? 'border-amber-600 bg-amber-950 text-amber-300'
                : 'border-zinc-700 bg-zinc-950 text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Pin size={13} />
            钉住
          </button>
          <button
            type="button"
            onClick={() => setArchivedView((value) => !value)}
            title={archivedView ? '回到夜空' : '看已归档的星'}
            className={`flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs transition-colors ${
              archivedView
                ? 'border-zinc-500 bg-zinc-800 text-zinc-200'
                : 'border-zinc-700 bg-zinc-950 text-zinc-400 hover:text-zinc-200'
            }`}
          >
            {archivedView ? <RotateCcw size={13} /> : <Archive size={13} />}
            {archivedView ? '回到夜空' : '归档'}
          </button>

          <span className="mx-1 h-4 w-px bg-zinc-800" />

          {/* 排序与视图切换都是"怎么看"而不是"看什么"，故而不算筛选，
              resetFilters 不动它们 */}
          <div className="flex h-8 items-center gap-0.5 rounded-md border border-zinc-700 bg-zinc-950 p-0.5">
            <button
              type="button"
              title="新收录的在前"
              aria-label="按收录时间排序"
              aria-pressed={sort === 'recent'}
              onClick={() => setSort('recent')}
              className={`h-7 rounded px-2 text-[11px] transition-colors ${
                sort === 'recent' ? 'bg-zinc-800 text-teal-300' : 'text-zinc-500 hover:text-zinc-200'
              }`}
            >
              新收录
            </button>
            <button
              type="button"
              title="最近回味过的在前（打开过详情的星）"
              aria-label="按回味时间排序"
              aria-pressed={sort === 'revisited'}
              onClick={() => setSort('revisited')}
              className={`flex h-7 items-center gap-1 rounded px-2 text-[11px] transition-colors ${
                sort === 'revisited' ? 'bg-zinc-800 text-teal-300' : 'text-zinc-500 hover:text-zinc-200'
              }`}
            >
              <Moon size={11} />
              常回味
            </button>
          </div>

          <div className="flex h-8 items-center gap-0.5 rounded-md border border-zinc-700 bg-zinc-950 p-0.5">
            <button
              type="button"
              title="星图模式"
              aria-label="星图模式"
              aria-pressed={view === 'sky'}
              onClick={() => setView('sky')}
              className={`flex h-7 w-7 items-center justify-center rounded transition-colors ${
                view === 'sky' ? 'bg-zinc-800 text-teal-300' : 'text-zinc-500 hover:text-zinc-200'
              }`}
            >
              <LayoutGrid size={14} />
            </button>
            <button
              type="button"
              title="清单模式"
              aria-label="清单模式"
              aria-pressed={view === 'list'}
              onClick={() => setView('list')}
              className={`flex h-7 w-7 items-center justify-center rounded transition-colors ${
                view === 'list' ? 'bg-zinc-800 text-teal-300' : 'text-zinc-500 hover:text-zinc-200'
              }`}
            >
              <List size={14} />
            </button>
          </div>

          <button
            type="button"
            onClick={() => void grabRandom()}
            title="随机抓三颗（R）"
            className="secondary-button h-8"
          >
            <Hand size={14} />
            伸手抓一把
          </button>
        </div>

        {(tag !== null || favoriteOnly || pinnedOnly || keywordInput !== '') && (
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
            <span>正在筛选：</span>
            {tag !== null && <Chip onClear={() => setTag(null)}>#{tag}</Chip>}
            {favoriteOnly && <Chip onClear={() => setFavoriteOnly(false)}>只看收藏</Chip>}
            {pinnedOnly && <Chip onClear={() => setPinnedOnly(false)}>只看钉住</Chip>}
            {keywordInput !== '' && <Chip onClear={() => setKeywordInput('')}>「{keywordInput}」</Chip>}
            <button type="button" onClick={resetFilters} className="text-teal-400 hover:underline">
              全部清除
            </button>
          </div>
        )}
      </div>

      {error && (
        <p className="mx-4 mb-2 shrink-0 rounded-md border border-red-900 bg-red-950/40 px-4 py-2 text-xs text-red-300 sm:mx-5">
          {error}
        </p>
      )}

      {/* ③ 夜空 / 清单 + ④ 抽屉 */}
      <div className="flex min-h-0 flex-1 gap-1.5 px-4 pb-4 sm:px-5">
        <div className="panel relative flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {view === 'sky' ? (
            // 与清单模式保持一致：只在"还没有任何星可看"时才整片换成骨架。
            // 否则点"再望远处一些"会让已有星星先闪没一次，像数据丢了
            loading && filtered.length === 0 ? (
              <StarField
                stars={[]}
                total={0}
                loading
                grabbedIds={grabbedIds}
                activeTag={tag}
                selectedId={selectedId}
                hasMore={false}
                onGrab={() => undefined}
                onLoadMore={loadMore}
              />
            ) : filteredButEmpty ? (
              <FilteredEmpty onClear={resetFilters} />
            ) : total === 0 ? (
              <SkyEmpty onCatch={focusCapture} onImport={() => setImportOpen(true)} archived={archivedView} />
            ) : (
              <StarField
                stars={filtered}
                total={total}
                loading={loading}
                grabbedIds={grabbedIds}
                activeTag={tag}
                selectedId={selectedId}
                hasMore={hasMore}
                onGrab={(star, rect) => void grabStar(star, rect)}
                onLoadMore={loadMore}
              />
            )
          ) : (
            <StarList
              stars={filtered}
              loading={loading}
              total={total}
              grabbedIds={grabbedIds}
              selectedId={selectedId}
              hasMore={hasMore}
              onGrab={(star, rect) => void grabStar(star, rect)}
              onLoadMore={loadMore}
              onCompose={focusCapture}
              archived={archivedView}
              filteredButEmpty={filteredButEmpty}
              onClearFilters={resetFilters}
            />
          )}
        </div>

        <StarDetailDrawer
          stars={drawerStars}
          pendingId={pendingId}
          originRect={originRect}
          onClose={closeDrawer}
          onEdit={(star) => {
            setEditing(star)
            setEditorOpen(true)
          }}
          onDelete={(star) => setDeleting(star)}
          onPatch={(star, patch) => void patchStar(star, patch)}
        />
      </div>

      {editorOpen && (
        <StarEditorDialog
          star={editing}
          initialContent={editing ? '' : draft}
          knownTags={tagList.map((item) => item.name)}
          onClose={() => setEditorOpen(false)}
          onSave={async (input) => {
            if (editing) {
              // 用后端返回的 saved 覆盖本地：tags 会在服务端 normalize_tags
              // （去重/截断/去空白），本地合并会留下未归一化的结果，
              // 而且 updated_at 不更新的话"改于"要等重开抽屉才出现
              const saved = await starApi.update(editing.id, input)
              setDrawerStars((current) =>
                current.map((item) => (item.id === saved.id ? saved : item)),
              )
              toast.ok('这颗星改好了')
              await Promise.all([loadPage(1, false), loadTags()])
              return
            }
            await createStar(input)
            setDraft('')
          }}
        />
      )}

      {importOpen && (
        <StarImportDialog
          knownTags={tagList.map((item) => item.name)}
          onClose={() => setImportOpen(false)}
          onImport={importStars}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title="删除这颗星"
          message={`确定删除「${deleting.preview}」吗？`}
          note="删掉就找不回来了。也可以先归档——划过夜空，之后仍能从「归档」里找回。"
          busy={deleteBusy}
          onConfirm={() => void removeStar()}
          onCancel={() => setDeleting(null)}
        />
      )}
    </div>
  )
}

/** 筛选条上的可移除小标签 */
function Chip({ children, onClear }: { children: React.ReactNode; onClear: () => void }) {
  return (
    <span className="flex items-center gap-1 rounded-md border border-zinc-700 bg-zinc-950 px-1.5 py-0.5 text-[11px] text-zinc-300">
      {children}
      <button type="button" onClick={onClear} aria-label="移除这个筛选" className="text-zinc-500 hover:text-zinc-200">
        <X size={11} />
      </button>
    </span>
  )
}

function FilteredEmpty({ onClear }: { onClear: () => void }) {
  return (
    <EmptyState
      icon={Search}
      title="这片天区没有星"
      description="当前的筛选条件下什么都没匹配到。星星还在天上，只是不在这片区域。"
      action={
        <button type="button" className="secondary-button" onClick={onClear}>
          <X size={15} />
          清除全部筛选
        </button>
      }
    />
  )
}

function SkyEmpty({
  onCatch,
  onImport,
  archived,
}: {
  onCatch: () => void
  onImport: () => void
  archived: boolean
}) {
  if (archived) {
    return (
      <EmptyState
        icon={Archive}
        title="没有归档的星"
        description="划过夜空的星会停在这里。在抽屉里点归档图标即可把一颗星收进来。"
      />
    )
  }
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 py-12 text-center">
      <span className="relative flex h-20 w-20 items-center justify-center">
        <span className="absolute inset-0 rounded-full ring-1 ring-inset ring-zinc-800" />
        <span className="absolute inset-4 rounded-full bg-teal-500/10 blur-[12px]" />
        <Sparkles className="relative text-zinc-500" size={26} strokeWidth={1.25} />
      </span>
      <h2 className="mt-5 text-base font-medium text-zinc-100">夜空还是空的</h2>
      <p className="mt-2 max-w-sm text-sm leading-6 text-zinc-400">
        一句没头没尾的话、半截想法、要记下的备忘——写下来就是一颗星。
        <br />
        不用分类，不用整理，先让它挂在天上。
      </p>
      <div className="mt-5 rounded-md border border-zinc-800 bg-zinc-950/60 px-4 py-3 text-left">
        <p className="text-[11px] text-zinc-500">比如：</p>
        <ul className="mt-1.5 space-y-1 text-xs text-zinc-400">
          <li>· 原来「中庸」不是和稀泥，是「时中」</li>
          <li>· 日语听力换成精听 + 影子跟读，试两周</li>
          <li>· 想要一个"能被偶然重新看见"的备忘录</li>
        </ul>
      </div>
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        <button type="button" className="primary-button" onClick={onCatch}>
          <Sparkles size={15} />
          写下第一颗星
        </button>
        <button type="button" className="secondary-button" onClick={onImport}>
          从别处搬一批过来
        </button>
      </div>
    </div>
  )
}

function StarList({
  stars,
  loading,
  total,
  grabbedIds,
  selectedId,
  hasMore,
  onGrab,
  onLoadMore,
  onCompose,
  archived,
  filteredButEmpty,
  onClearFilters,
}: {
  stars: StarBrief[]
  loading: boolean
  total: number
  grabbedIds: ReadonlySet<string>
  selectedId: string | null
  hasMore: boolean
  onGrab: (star: StarBrief, rect: DOMRect) => void
  onLoadMore: () => void
  onCompose: () => void
  archived: boolean
  filteredButEmpty: boolean
  onClearFilters: () => void
}) {
  if (loading && stars.length === 0) {
    return (
      <div className="space-y-1 p-2" aria-busy="true" aria-label="正在加载星星">
        {[0, 1, 2, 3, 4, 5].map((row) => (
          <div key={row} className="rounded-md border border-transparent px-3 py-3">
            <div className="flex items-center gap-2">
              <div className="skeleton h-4 w-12" />
              <div className="skeleton ml-auto h-3 w-20" />
            </div>
            <div className="skeleton mt-2.5 h-4 w-3/5" />
            <div className="skeleton mt-2 h-3 w-2/5" />
          </div>
        ))}
      </div>
    )
  }

  if (total === 0) {
    return filteredButEmpty ? (
      <FilteredEmpty onClear={onClearFilters} />
    ) : (
      <EmptyState
        icon={Star}
        title="这里没有星"
        description={archived ? '归档里也空着。' : '换个筛选条件试试，或者直接写下一念。'}
        action={
          <button type="button" className="primary-button" onClick={onCompose}>
            <Sparkles size={15} />
            写下一念
          </button>
        }
      />
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        <div className="space-y-1">
          {stars.map((star, index) => (
            <button
              key={star.id}
              type="button"
              onClick={(event) => onGrab(star, event.currentTarget.getBoundingClientRect())}
              aria-current={star.id === selectedId || undefined}
              className={`block w-full rounded-md border px-3 py-2.5 text-left transition-colors ${
                star.id === selectedId
                  ? 'border-teal-700 bg-teal-950/50'
                  : 'border-transparent hover:border-zinc-700 hover:bg-zinc-800/40'
              }`}
            >
              <span className="flex items-center gap-2">
                {star.is_pinned && <Pin size={12} className="shrink-0 text-amber-400" />}
                {star.is_favorite && (
                  <Star size={12} className="shrink-0 text-amber-300" fill="currentColor" />
                )}
                <span className="text-[11px] text-zinc-600">{index + 1}</span>
                <span className="ml-auto flex shrink-0 items-center gap-1.5 text-[11px] text-zinc-500">
                  {grabbedIds.has(star.id) && <span className="text-teal-600">· 已抓过</span>}
                  {new Date(star.created_at).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })}
                </span>
              </span>
              <span className="mt-1 block text-sm leading-6 text-zinc-200">{star.preview}</span>
              {star.tags.length > 0 && (
                <span className="mt-1 flex flex-wrap gap-1.5">
                  {star.tags.map((name) => (
                    <span
                      key={name}
                      className="rounded border border-zinc-700 px-1 py-px text-[10px] text-zinc-500"
                    >
                      #{name}
                    </span>
                  ))}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="flex shrink-0 items-center justify-between gap-3 border-t border-zinc-800 px-3 py-2 text-[11px] text-zinc-500">
        <span>
          {total > MAX_RENDERED ? `已显示 ${stars.length} / ${total} 颗` : `共 ${total} 颗`}
        </span>
        {hasMore && (
          <button
            type="button"
            onClick={onLoadMore}
            className="rounded-md border border-zinc-700 bg-zinc-950 px-2 py-0.5 text-[11px] text-zinc-300 transition-colors hover:border-teal-600 hover:text-teal-300"
          >
            再望远处一些
          </button>
        )}
      </div>
    </div>
  )
}
