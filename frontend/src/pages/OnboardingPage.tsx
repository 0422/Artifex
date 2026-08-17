import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { pathApi } from '../services/api'
import type { Domain, OnboardingQuestion } from '../lib/types'

const DOMAIN_OPTIONS: { value: Domain; label: string }[] = [
  { value: 'language', label: '外语' },
  { value: 'humanities', label: '人文社科' },
  { value: 'skill', label: '技能' },
]

export default function OnboardingPage() {
  const [questions, setQuestions] = useState<OnboardingQuestion[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [domain, setDomain] = useState<Domain>('language')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    pathApi.getOnboarding().then(setQuestions)
  }, [])

  const submit = async () => {
    setLoading(true)
    try {
      // domain 单独提交，其余问题（去掉 domain 那题）作为 answers
      const rest = { ...answers }
      delete rest.domain
      await pathApi.completeOnboarding(domain, rest)
      navigate('/path')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="mb-2 text-2xl font-semibold text-slate-100">5 分钟引导</h1>
      <p className="mb-8 text-sm text-slate-400">回答几个问题，Artifex 会为你生成专属学习起点报告和路径。</p>

      <div className="space-y-6">
        {questions.map((q) => (
          <div key={q.key}>
            <label className="mb-2 block text-sm font-medium text-slate-200">{q.question}</label>
            {q.hint && <p className="mb-2 text-xs text-slate-500">{q.hint}</p>}
            {q.key === 'domain' ? (
              <div className="flex gap-2">
                {DOMAIN_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setDomain(opt.value)}
                    className={`rounded-lg px-4 py-2 text-sm ${
                      domain === opt.value ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            ) : (
              <input
                type="text"
                value={answers[q.key] ?? ''}
                onChange={(e) => setAnswers((a) => ({ ...a, [q.key]: e.target.value }))}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-indigo-500"
              />
            )}
          </div>
        ))}
      </div>

      <button
        onClick={submit}
        disabled={loading}
        className="mt-8 w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
      >
        {loading ? '正在生成学习路径…' : '完成引导，生成路径'}
      </button>
    </div>
  )
}
