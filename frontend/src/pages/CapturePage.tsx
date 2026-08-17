import { useState } from 'react'

import { captureApi } from '../services/api'
import type { Concept, Domain } from '../lib/types'

const DOMAIN_OPTIONS: { value: Domain; label: string }[] = [
  { value: 'language', label: '外语' },
  { value: 'humanities', label: '人文社科' },
  { value: 'skill', label: '技能' },
]

// 轮询捕获状态，直到 completed/failed
async function pollUntilDone(id: string, onTick: (status: string) => void): Promise<void> {
  for (let i = 0; i < 30; i++) {
    const cap = await captureApi.getStatus(id)
    onTick(cap.status)
    if (cap.status === 'completed' || cap.status === 'failed') return
    await new Promise((r) => setTimeout(r, 2000))
  }
}

export default function CapturePage() {
  const [content, setContent] = useState('')
  const [domain, setDomain] = useState<Domain>('humanities')
  const [status, setStatus] = useState('')
  const [summary, setSummary] = useState('')
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [busy, setBusy] = useState(false)

  const extract = async () => {
    if (!content.trim()) return
    setBusy(true)
    setConcepts([])
    setSummary('')
    setStatus('提交中…')
    try {
      const cap = await captureApi.create(domain, 'text', content)
      setStatus('处理中…')
      await pollUntilDone(cap.id, (s) => setStatus(s === 'processing' ? 'AI 正在提取概念…' : s))
      const result = await captureApi.getConcepts(cap.id)
      setSummary(result.capture.summary ?? '')
      setConcepts(result.concepts)
      setStatus(result.capture.status === 'completed' ? '完成' : '处理失败')
    } catch {
      setStatus('出错了，请重试')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="mb-1 text-2xl font-semibold text-slate-100">内容捕获</h1>
      <p className="mb-6 text-sm text-slate-400">
        粘贴文章，Artifex 会自动提取关键概念、生成记忆卡片。
      </p>

      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="粘贴你想学习的内容…"
        className="min-h-40 w-full rounded-xl border border-slate-700 bg-slate-900 p-4 text-sm text-slate-100 outline-none focus:border-indigo-500"
      />

      <div className="mt-4 flex gap-3">
        <select
          value={domain}
          onChange={(e) => setDomain(e.target.value as Domain)}
          className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100"
        >
          {DOMAIN_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <button
          onClick={extract}
          disabled={busy}
          className="rounded-lg bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {busy ? '处理中…' : '提取概念'}
        </button>
      </div>

      {status && <p className="mt-4 text-sm text-slate-400">状态：{status}</p>}

      {summary && (
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="mb-1 text-xs text-slate-500">摘要</div>
          <p className="text-sm text-slate-200">{summary}</p>
        </div>
      )}

      {concepts.length > 0 && (
        <div className="mt-6 space-y-3">
          <div className="text-sm text-slate-400">提取到 {concepts.length} 个概念</div>
          {concepts.map((c) => (
            <div key={c.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-1 font-medium text-slate-100">{c.label}</div>
              {c.definition && <p className="text-sm text-slate-400">{c.definition}</p>}
              <div className="mt-2 flex gap-2">
                <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs text-emerald-400">
                  已生成 {c.card_count} 张卡片
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
