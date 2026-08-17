import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { AxiosError } from 'axios'

import { pathApi } from '../services/api'
import type { LearningPath } from '../lib/types'

const STATUS_STYLE: Record<string, { label: string; cls: string }> = {
  completed: { label: '已完成', cls: 'bg-emerald-500/15 text-emerald-400' },
  current: { label: '进行中', cls: 'bg-indigo-500/15 text-indigo-400' },
  locked: { label: '待解锁', cls: 'bg-slate-700 text-slate-400' },
}

export default function PathPage() {
  const [path, setPath] = useState<LearningPath | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    pathApi
      .getCurrent()
      .then(setPath)
      .catch((err: AxiosError) => {
        if (err.response?.status === 404) navigate('/onboarding')
      })
      .finally(() => setLoading(false))
  }, [navigate])

  if (loading) return <div className="px-4 py-10 text-slate-400">加载中…</div>
  if (!path) return null

  const report = path.starting_point_report

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <Link to="/tools" title="返回工具库" aria-label="返回工具库" className="icon-button mb-5"><ArrowLeft size={19} /></Link>
      <h1 className="mb-1 text-2xl font-semibold text-slate-100">{path.title}</h1>
      <p className="mb-6 text-sm text-slate-400">基于你的引导结果自动生成</p>

      {report && (
        <div className="mb-8 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <h2 className="mb-3 text-sm font-medium text-indigo-400">学习起点报告</h2>
          {report.level_summary && <p className="mb-3 text-sm text-slate-200">{report.level_summary}</p>}
          <div className="grid gap-4 sm:grid-cols-2">
            {report.strengths && (
              <div>
                <div className="mb-1 text-xs text-slate-500">优势</div>
                <ul className="list-inside list-disc text-sm text-slate-300">
                  {report.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            {report.gaps && (
              <div>
                <div className="mb-1 text-xs text-slate-500">待补齐</div>
                <ul className="list-inside list-disc text-sm text-slate-300">
                  {report.gaps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          {report.recommendation && (
            <p className="mt-3 text-sm text-slate-400">建议：{report.recommendation}</p>
          )}
        </div>
      )}

      <div className="space-y-4 border-l border-slate-800 pl-6">
        {path.milestones.map((m) => {
          const style = STATUS_STYLE[m.status] ?? STATUS_STYLE.locked
          return (
            <div key={m.id} className="relative">
              <span className="absolute -left-[29px] top-1.5 h-3 w-3 rounded-full border-2 border-slate-950 bg-indigo-500" />
              <div className="mb-1 flex items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs ${style.cls}`}>{style.label}</span>
                <span className="text-xs text-slate-500">第 {m.order_index + 1} 阶段</span>
              </div>
              <h3 className="font-medium text-slate-100">{m.title}</h3>
              {m.description && <p className="mt-1 text-sm text-slate-400">{m.description}</p>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
