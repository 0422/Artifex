import { useEffect, useState } from 'react'
import { BarChart3, ChevronLeft, ChevronRight, Clock3, MessageSquareText, Target, X } from 'lucide-react'

import { dashboardApi } from '../services/api'
import type { DashboardOverview, DashboardSessionDetail, DashboardSessionPage, ReportStatus } from '../lib/types'

const STATUS: Record<ReportStatus, { label: string; className: string }> = {
  ready: { label: '报告已生成', className: 'text-emerald-400' },
  degraded: { label: '备用报告', className: 'text-amber-400' },
  insufficient_data: { label: '数据不足', className: 'text-amber-400' },
  missing: { label: '暂无报告', className: 'text-zinc-500' },
  invalid: { label: '报告异常', className: 'text-red-400' },
}

const duration = (seconds: number) => seconds < 60 ? `${seconds} 秒` : `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
const dateTime = (value: string) => new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))

export default function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [sessions, setSessions] = useState<DashboardSessionPage | null>(null)
  const [page, setPage] = useState(1)
  const [detail, setDetail] = useState<DashboardSessionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([dashboardApi.overview(), dashboardApi.sessions(page)])
      .then(([overviewData, sessionData]) => { setOverview(overviewData); setSessions(sessionData) })
      .catch(() => setError('学习数据加载失败，请稍后重试'))
      .finally(() => setLoading(false))
  }, [page])

  const changePage = (nextPage: number) => {
    setLoading(true)
    setPage(nextPage)
  }

  const openDetail = async (id: string) => {
    setError('')
    try { setDetail(await dashboardApi.session(id)) } catch { setError('会话详情加载失败') }
  }

  if (loading && !overview) return <div className="p-8 text-sm text-zinc-500">正在加载学习数据...</div>

  return (
    <div className="min-h-full bg-zinc-900 px-4 py-7 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-7"><h1 className="text-xl font-semibold text-zinc-100">仪表盘</h1><p className="mt-1 text-sm text-zinc-500">查看情境对话练习进度和常见薄弱点</p></div>
        {error && <p className="mb-4 border-l-2 border-red-500 bg-red-950/30 px-3 py-2 text-sm text-red-300">{error}</p>}

        <section className="grid border-y border-zinc-800 sm:grid-cols-2 lg:grid-cols-4">
          <Metric icon={<MessageSquareText size={18} />} label="完成对话" value={`${overview?.total_conversations ?? 0} 次`} />
          <Metric icon={<Clock3 size={18} />} label="练习时长" value={duration(overview?.total_duration_seconds ?? 0)} />
          <Metric icon={<Target size={18} />} label="平均表现" value={overview?.average_performance_score == null ? '--' : `${overview.average_performance_score.toFixed(1)} 分`} />
          <Metric icon={<BarChart3 size={18} />} label="已评分会话" value={`${overview?.scored_conversations ?? 0} 次`} />
        </section>

        <div className="mt-8 grid gap-8 lg:grid-cols-2">
          <section><h2 className="text-sm font-semibold text-zinc-200">场景练习分布</h2>
            <div className="mt-4 space-y-3">{overview?.scenario_distribution.length ? overview.scenario_distribution.map((item) => {
              const max = Math.max(...overview.scenario_distribution.map((entry) => entry.count))
              return <div key={`${item.scenario_id}-${item.title}`}><div className="mb-1 flex justify-between text-xs"><span className="text-zinc-400">{item.title}</span><span className="text-zinc-500">{item.count} 次</span></div><div className="h-1.5 overflow-hidden rounded bg-zinc-800"><div className="h-full bg-teal-500" style={{ width: `${item.count / max * 100}%` }} /></div></div>
            }) : <Empty text="完成一次对话后会显示场景分布" />}</div>
          </section>
          <section><h2 className="text-sm font-semibold text-zinc-200">高频薄弱点</h2>
            <div className="mt-4 divide-y divide-zinc-800 border-y border-zinc-800">{overview?.frequent_weak_points.length ? overview.frequent_weak_points.map((item) => <div key={item.tag} className="flex items-center justify-between py-3"><div><span className="mr-2 rounded bg-amber-950 px-2 py-0.5 text-xs text-amber-300">{item.category}</span><span className="text-sm text-zinc-300">{item.tag.split(':')[1].replaceAll('_', ' ')}</span></div><span className="text-xs text-zinc-500">{item.count} 次</span></div>) : <Empty text="生成学习报告后会归纳薄弱点" />}</div>
          </section>
        </div>

        <section className="mt-10">
          <div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-semibold text-zinc-200">对话记录</h2><span className="text-xs text-zinc-500">共 {sessions?.total ?? 0} 条</span></div>
          <div className="overflow-x-auto border-y border-zinc-800">
            <table className="w-full min-w-[680px] text-left text-sm"><thead className="text-xs text-zinc-500"><tr><th className="px-3 py-3 font-medium">场景</th><th className="px-3 py-3 font-medium">时间</th><th className="px-3 py-3 font-medium">时长</th><th className="px-3 py-3 font-medium">表现</th><th className="px-3 py-3 font-medium">报告</th></tr></thead>
              <tbody className="divide-y divide-zinc-800">{sessions?.items.map((item) => <tr key={item.id} onClick={() => openDetail(item.id)} className="cursor-pointer text-zinc-300 hover:bg-zinc-800/50"><td className="px-3 py-3"><span className="font-medium text-zinc-200">{item.scenario_title}</span><span className="ml-2 text-xs text-zinc-500">{item.difficulty}</span></td><td className="px-3 py-3 text-zinc-500">{dateTime(item.created_at)}</td><td className="px-3 py-3">{duration(item.duration_seconds)}</td><td className="px-3 py-3">{item.performance_score ?? '--'}</td><td className={`px-3 py-3 text-xs ${STATUS[item.report_status].className}`}>{STATUS[item.report_status].label}</td></tr>)}</tbody>
            </table>
            {!sessions?.items.length && <Empty text="还没有对话记录，从情境对话开始第一次练习" />}
          </div>
          {(sessions?.total ?? 0) > (sessions?.page_size ?? 20) && <div className="mt-4 flex justify-end gap-2"><button title="上一页" disabled={page === 1 || loading} onClick={() => changePage(page - 1)} className="icon-button"><ChevronLeft size={17} /></button><span className="px-2 py-2 text-xs text-zinc-500">第 {page} 页</span><button title="下一页" disabled={loading || page * (sessions?.page_size ?? 20) >= (sessions?.total ?? 0)} onClick={() => changePage(page + 1)} className="icon-button"><ChevronRight size={17} /></button></div>}
        </section>
      </div>
      {detail && <SessionDetail detail={detail} onClose={() => setDetail(null)} />}
    </div>
  )
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="border-b border-zinc-800 p-5 last:border-b-0 sm:border-r sm:[&:nth-child(2)]:border-r-0 lg:border-b-0 lg:[&:nth-child(2)]:border-r lg:last:border-r-0"><div className="flex items-center gap-2 text-teal-400">{icon}<span className="text-xs text-zinc-500">{label}</span></div><p className="mt-3 text-2xl font-semibold text-zinc-100">{value}</p></div>
}

function Empty({ text }: { text: string }) { return <p className="py-8 text-center text-sm text-zinc-600">{text}</p> }

function SessionDetail({ detail, onClose }: { detail: DashboardSessionDetail; onClose: () => void }) {
  return <div className="fixed inset-0 z-50 flex justify-end bg-black/70" onClick={onClose}><aside className="h-full w-full max-w-xl overflow-y-auto border-l border-zinc-700 bg-zinc-900 p-6 shadow-2xl" onClick={(event) => event.stopPropagation()}><div className="flex items-start justify-between"><div><p className="text-xs text-zinc-500">{dateTime(detail.created_at)}</p><h2 className="mt-1 text-lg font-semibold text-zinc-100">{detail.scenario_title}</h2><p className="mt-1 text-sm text-zinc-500">{detail.language.toUpperCase()} · {detail.difficulty} · {duration(detail.duration_seconds)}</p></div><button title="关闭" onClick={onClose} className="icon-button"><X size={17} /></button></div>
    {detail.report ? <div className="mt-8"><div className="border-y border-zinc-800 py-5"><p className="text-xs text-zinc-500">表现评分</p><p className="mt-1 text-3xl font-semibold text-teal-300">{detail.report.performance_score ?? '--'}<span className="text-xs text-zinc-500"> / 100</span></p></div><h3 className="mt-6 text-sm font-medium text-zinc-200">总结</h3><p className="mt-2 text-sm leading-6 text-zinc-400">{detail.report.summary}</p><h3 className="mt-6 text-sm font-medium text-zinc-200">薄弱点</h3><div className="mt-2 divide-y divide-zinc-800">{detail.report.weak_points.map((point) => <div key={point.tag} className="py-4"><p className="text-sm text-zinc-300">{point.description}</p><p className="mt-1 text-xs text-teal-300">{point.suggestion}</p></div>)}</div><h3 className="mt-6 text-sm font-medium text-zinc-200">建议</h3><ol className="mt-2 space-y-2 text-sm text-zinc-400">{detail.report.suggestions.map((suggestion, index) => <li key={index}>{index + 1}. {suggestion}</li>)}</ol></div> : <Empty text="本次会话没有可用报告" />}
  </aside></div>
}
