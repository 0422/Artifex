import { Newspaper, RefreshCw, Sparkles } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { format } from 'date-fns'

import EmptyState from '../components/EmptyState'
// 2026-10-03 修复 ReferenceError: NewsSourcesDialog is not defined——使用时漏了 import，
// 因 {sourcesOpen && ...} 短路求值，只在点开「来源管理」时才暴露
import NewsSourcesDialog from '../components/NewsSourcesDialog'
import { newsApi } from '../services/api'
import { toast } from '../stores/toastStore'
import {
  NEWS_DOMAIN_LABELS,
  type NewsDigest,
  type NewsDigestListItem,
  type NewsDomain,
} from '../lib/types'

// 2026-10-03 新增世势洞察（M6）主页面：板块筛选 + 日报卡片流。
// 列表接口只回摘要（不含 items），点开卡片时才按 id 拉详情并缓存，
// 与知识库/仪表盘「列表轻、详情按需」的既有节奏一致。

const DOMAIN_FILTERS: Array<{ key: NewsDomain | 'all'; label: string }> = [
  { key: 'all', label: '全部' },
  ...(Object.keys(NEWS_DOMAIN_LABELS) as NewsDomain[]).map((key) => ({
    key,
    label: NEWS_DOMAIN_LABELS[key],
  })),
]

function importanceBadgeClass(value: number): string {
  if (value >= 8) return 'border-teal-700 bg-teal-950 text-teal-300'
  if (value >= 6) return 'border-amber-800 bg-amber-950 text-amber-300'
  return 'border-zinc-700 bg-zinc-800 text-zinc-400'
}

function formatDateTime(value: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : format(date, 'MM-dd HH:mm')
}

export default function NewsInsightPage() {
  const [digests, setDigests] = useState<NewsDigestListItem[]>([])
  const [domain, setDomain] = useState<NewsDomain | 'all'>('all')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<'fetch' | 'generate' | null>(null)
  const [error, setError] = useState('')
  const [sourcesOpen, setSourcesOpen] = useState(false)
  // 已加载过详情的日报缓存：id -> 详情。展开时按需拉取，重复展开不再请求
  const [details, setDetails] = useState<Record<string, NewsDigest>>({})
  const [expandedId, setExpandedId] = useState<string | null>(null)
  // 2026-10-03 修复「第一条收起不了」：原来的自动展开 effect 把 expandedId 放进了
  // 依赖，点收起把它置 null 后 effect 立刻又把第一条弹开。改用 ref 做一次性守卫，
  // 只有列表首次就绪时自动展开一次，之后完全交给用户控制
  const autoExpandedRef = useRef(false)

  const loadDigests = useCallback((next: NewsDomain | 'all') => {
    setLoading(true)
    newsApi
      .digests(next === 'all' ? undefined : next)
      .then((data) => setDigests(data.items))
      .catch(() => setError('日报加载失败，请稍后重试'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadDigests(domain)
  }, [domain, loadDigests])

  // 切板块时重置展开态与自动展开标记，让新列表的第一条重新自动展开
  useEffect(() => {
    setExpandedId(null)
    autoExpandedRef.current = false
  }, [domain])

  // 列表就绪后自动展开第一条，页面打开即可读到最新日报（仅一次，见 autoExpandedRef）
  useEffect(() => {
    if (!loading && digests.length > 0 && !autoExpandedRef.current) {
      autoExpandedRef.current = true
      setExpandedId(digests[0].id)
    }
  }, [loading, digests])

  const openDetail = (id: string) => {
    setExpandedId((current) => (current === id ? null : id))
    if (!details[id]) {
      newsApi
        .digest(id)
        .then((detail) => setDetails((prev) => ({ ...prev, [id]: detail })))
        .catch(() => toast.error('日报详情加载失败'))
    }
  }

  const onFetch = () => {
    setBusy('fetch')
    newsApi
      .fetch()
      .then((result) => {
        toast.ok(
          `抓取完成：${result.succeeded}/${result.total_sources} 个源成功，新增 ${result.new_articles} 篇`,
        )
      })
      .catch(() => toast.error('抓取失败，请稍后重试'))
      .finally(() => setBusy(null))
  }

  const onGenerate = () => {
    setBusy('generate')
    newsApi
      .generate(domain === 'all' ? {} : { domain })
      .then((list) => {
        if (list.length === 0) {
          toast.error('窗口内没有抓到文章，先点「抓取」试试')
          return
        }
        toast.ok(`已生成 ${list.length} 份日报`)
        setDetails((prev) => {
          const next = { ...prev }
          for (const digest of list) next[digest.id] = digest
          return next
        })
        loadDigests(domain)
      })
      .catch(() => toast.error('日报生成失败，请稍后重试'))
      .finally(() => setBusy(null))
  }

  return (
    <div className="panel h-full overflow-y-auto px-4 py-7 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-4xl">
        <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-zinc-100">世势洞察</h1>
            <p className="mt-1 text-sm text-zinc-400">订阅源定时抓取，AI 按板块每日策展成中文简报</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="secondary-button"
              disabled={busy !== null}
              onClick={() => setSourcesOpen(true)}
            >
              来源管理
            </button>
            <button
              type="button"
              className="secondary-button"
              disabled={busy !== null}
              onClick={onFetch}
            >
              <RefreshCw size={15} className={busy === 'fetch' ? 'animate-spin' : undefined} />
              {busy === 'fetch' ? '抓取中…' : '抓取'}
            </button>
            <button
              type="button"
              className="primary-button"
              disabled={busy !== null}
              onClick={onGenerate}
            >
              <Sparkles size={15} />
              {busy === 'generate' ? '生成中…' : '生成今日日报'}
            </button>
          </div>
        </header>

        {error && (
          <p className="mb-4 rounded-md border border-red-900 bg-red-950/40 px-4 py-2 text-sm text-red-300">
            {error}
          </p>
        )}

        <div className="mb-5 flex flex-wrap gap-2">
          {DOMAIN_FILTERS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setDomain(key)}
              className={`rounded-md border px-3 py-1 text-xs transition-colors ${
                domain === key
                  ? 'border-teal-600 bg-teal-950 text-teal-300'
                  : 'border-zinc-700 bg-zinc-950 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {loading ? (
          <DigestsSkeleton />
        ) : digests.length === 0 ? (
          <EmptyState
            icon={Newspaper}
            title="还没有日报"
            description="点「抓取」拉取订阅源更新，再点「生成今日日报」让 AI 按板块策展。"
            action={
              <button type="button" className="primary-button" onClick={onGenerate} disabled={busy !== null}>
                生成今日日报
              </button>
            }
          />
        ) : (
          <div className="space-y-4">
            {digests.map((item) => (
              <DigestCard
                key={item.id}
                item={item}
                detail={details[item.id]}
                expanded={expandedId === item.id}
                onToggle={() => openDetail(item.id)}
              />
            ))}
          </div>
        )}
      </div>

      {sourcesOpen && <NewsSourcesDialog onClose={() => setSourcesOpen(false)} />}
    </div>
  )
}

function DigestCard({
  item,
  detail,
  expanded,
  onToggle,
}: {
  item: NewsDigestListItem
  detail: NewsDigest | undefined
  expanded: boolean
  onToggle: () => void
}) {
  const published = formatDateTime(item.created_at)
  return (
    <article className="panel overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-3 border-b border-zinc-800 px-5 py-4 text-left transition-colors hover:bg-zinc-800/40"
      >
        <span className="rounded-md border border-teal-800 bg-teal-950 px-2 py-0.5 text-[11px] font-medium text-teal-300">
          {NEWS_DOMAIN_LABELS[item.domain]}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium text-zinc-100">{item.title}</span>
          <span className="mt-0.5 block text-xs text-zinc-500">
            {item.article_count} 篇素材
            {published ? ` · 生成于 ${published}` : ''}
          </span>
        </span>
        {item.degraded && (
          <span className="rounded-md border border-amber-800 bg-amber-950 px-2 py-0.5 text-[11px] text-amber-300">
            降级稿
          </span>
        )}
        <span className="text-xs text-zinc-500">{expanded ? '收起' : '展开'}</span>
      </button>

      {expanded && (
        <div className="space-y-4 px-5 py-4">
          {detail === undefined ? (
            <p className="text-sm text-zinc-500">详情加载中…</p>
          ) : (
            <>
              {detail.summary && (
                <p className="text-sm leading-6 text-zinc-300">{detail.summary}</p>
              )}
              <ul className="space-y-4">
                {detail.items.map((entry, index) => {
                  const when = formatDateTime(entry.published_at)
                  const content = (
                    <>
                      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                        <h3 className="font-medium leading-6 text-zinc-100">
                          {entry.url ? (
                            <a
                              href={entry.url}
                              target="_blank"
                              rel="noreferrer"
                              className="hover:text-teal-300 hover:underline"
                            >
                              {entry.headline}
                            </a>
                          ) : (
                            entry.headline
                          )}
                        </h3>
                        {entry.importance > 0 && (
                          <span
                            className={`shrink-0 rounded-md border px-1.5 py-0.5 text-[11px] font-medium ${importanceBadgeClass(entry.importance)}`}
                          >
                            重要度 {entry.importance}
                          </span>
                        )}
                      </div>
                      {entry.summary_zh && (
                        <p className="mt-1 text-sm leading-6 text-zinc-300">{entry.summary_zh}</p>
                      )}
                      {entry.why_matters && (
                        <p className="mt-1 text-xs leading-5 text-zinc-500">
                          为何值得关注：{entry.why_matters}
                        </p>
                      )}
                      {(entry.source_name || when) && (
                        <p className="mt-1 text-[11px] text-zinc-500">
                          {entry.source_name}
                          {entry.source_name && when ? ' · ' : ''}
                          {when}
                        </p>
                      )}
                    </>
                  )
                  return entry.url ? (
                    <li key={`${entry.url}-${index}`} className="border-l-2 border-zinc-800 pl-4">
                      {content}
                    </li>
                  ) : (
                    <li key={`item-${index}`} className="border-l-2 border-zinc-800 pl-4">
                      {content}
                    </li>
                  )
                })}
              </ul>
            </>
          )}
        </div>
      )}
    </article>
  )
}

function DigestsSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1, 2].map((index) => (
        <div key={index} className="panel space-y-3 p-5">
          <div className="skeleton h-5 w-1/3" />
          <div className="skeleton h-4 w-full" />
          <div className="skeleton h-4 w-4/5" />
        </div>
      ))}
    </div>
  )
}
