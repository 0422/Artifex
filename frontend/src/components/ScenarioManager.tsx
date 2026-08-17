import { useEffect, useState } from 'react'
import { Check, Pencil, Plus, Trash2, X } from 'lucide-react'

import { scenarioApi } from '../services/api'
import type { Scenario, ScenarioDifficulty, ScenarioInput, ScenarioLanguage } from '../lib/types'

const LEVELS: Record<ScenarioLanguage, ScenarioDifficulty[]> = {
  en: ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
  ja: ['N5', 'N4', 'N3', 'N2', 'N1'],
  zh: ['beginner', 'intermediate', 'advanced'],
}

const EMPTY: ScenarioInput = { title: '', description: '', language: 'ja', difficulty: 'N3', domain: 'language', scenario_mode: 'role_play', estimated_minutes: 15, tags: [], category_ids: [] }

interface Props {
  requestedId?: string | null
  selectedId: string | null
  disabled?: boolean
  onSelect: (scenario: Scenario) => void
  onClose?: () => void
}

export default function ScenarioManager({ requestedId, selectedId, disabled, onSelect, onClose }: Props) {
  const [items, setItems] = useState<Scenario[]>([])
  const [editing, setEditing] = useState<Scenario | 'new' | null>(null)
  const [form, setForm] = useState<ScenarioInput>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    scenarioApi.list().then((data) => {
      setItems(data)
      if (!selectedId) {
        const requested = requestedId ? data.find((item) => item.id === requestedId) : undefined
        if (requested ?? data[0]) onSelect(requested ?? data[0])
      }
    }).catch(() => setError('场景加载失败')).finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const openEditor = (item?: Scenario) => {
    setError('')
    setEditing(item ?? 'new')
    setForm(item ? {
      title: item.title,
      description: item.description,
      language: item.language,
      difficulty: item.difficulty,
      domain: item.domain,
      scenario_mode: item.scenario_mode,
      estimated_minutes: item.estimated_minutes,
      tags: item.tags,
      category_ids: item.categories.map((category) => category.id),
    } : EMPTY)
  }

  const save = async () => {
    if (!form.title.trim() || !form.description.trim()) return
    setSaving(true)
    setError('')
    try {
      const saved = editing === 'new'
        ? await scenarioApi.create(form)
        : await scenarioApi.update((editing as Scenario).id, form)
      setItems((current) => editing === 'new'
        ? [...current, saved]
        : current.map((item) => item.id === saved.id ? saved : item))
      onSelect(saved)
      setEditing(null)
    } catch {
      setError('保存失败，请检查输入后重试')
    } finally {
      setSaving(false)
    }
  }

  const remove = async (item: Scenario) => {
    if (!window.confirm(`停用场景“${item.title}”？历史会话不会被删除。`)) return
    try {
      await scenarioApi.remove(item.id)
      const remaining = items.filter((current) => current.id !== item.id)
      setItems(remaining)
      if (selectedId === item.id && remaining[0]) onSelect(remaining[0])
    } catch {
      setError('停用场景失败')
    }
  }

  return (
    <section className="flex h-full min-h-0 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="flex h-14 items-center justify-between border-b border-zinc-800 px-4">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100">练习场景</h2>
          <p className="text-xs text-zinc-500">选择一个情境开始对话</p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button title="新建场景" disabled={disabled} onClick={() => openEditor()} className="icon-button">
            <Plus size={17} />
          </button>
          {onClose && <span className="lg:hidden"><button title="收起场景" aria-label="收起场景" onClick={onClose} className="icon-button"><X size={17} /></button></span>}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {loading && <p className="p-3 text-sm text-zinc-500">正在加载场景...</p>}
        {!loading && items.length === 0 && <p className="p-3 text-sm text-zinc-500">还没有可用场景</p>}
        {items.map((item) => (
          <div key={item.id} className={`group mb-1 flex items-start gap-2 rounded-md border px-3 py-3 ${selectedId === item.id ? 'border-teal-700 bg-teal-950/40' : 'border-transparent hover:bg-zinc-900'}`}>
            <button disabled={disabled} onClick={() => onSelect(item)} className="min-w-0 flex-1 text-left">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium text-zinc-100">{item.title}</span>
                <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">{item.difficulty}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-zinc-500">{item.description}</p>
            </button>
            {!disabled && (
              <div className="hidden shrink-0 gap-1 group-hover:flex">
                <button title="编辑" onClick={() => openEditor(item)} className="icon-button h-7 w-7"><Pencil size={13} /></button>
                <button title="停用" onClick={() => remove(item)} className="icon-button h-7 w-7 hover:text-red-400"><Trash2 size={13} /></button>
              </div>
            )}
          </div>
        ))}
      </div>
      {error && <p className="border-t border-zinc-800 px-4 py-2 text-xs text-red-400">{error}</p>}

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl">
            <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
              <h3 className="font-semibold text-zinc-100">{editing === 'new' ? '新建练习场景' : '编辑练习场景'}</h3>
              <button title="关闭" onClick={() => setEditing(null)} className="icon-button"><X size={17} /></button>
            </div>
            <div className="space-y-4 p-5">
              <label className="block text-sm text-zinc-300">场景名称
                <input autoFocus value={form.title} maxLength={100} onChange={(e) => setForm({ ...form, title: e.target.value })} className="field mt-1.5" placeholder="例如：在咖啡店点单" />
              </label>
              <label className="block text-sm text-zinc-300">情境说明
                <textarea value={form.description} maxLength={2000} onChange={(e) => setForm({ ...form, description: e.target.value })} className="field mt-1.5 min-h-28 resize-y" placeholder="说明角色、目标和对话背景" />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block text-sm text-zinc-300">语言
                  <select value={form.language} onChange={(e) => {
                    const language = e.target.value as ScenarioLanguage
                    setForm({ ...form, language, difficulty: LEVELS[language][0] })
                  }} className="field mt-1.5">
                    <option value="ja">日语</option><option value="en">英语</option><option value="zh">中文</option>
                  </select>
                </label>
                <label className="block text-sm text-zinc-300">难度
                  <select value={form.difficulty} onChange={(e) => setForm({ ...form, difficulty: e.target.value as ScenarioDifficulty })} className="field mt-1.5">
                    {LEVELS[form.language].map((level) => <option key={level}>{level}</option>)}
                  </select>
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-zinc-800 px-5 py-4">
              <button onClick={() => setEditing(null)} className="secondary-button"><X size={15} />取消</button>
              <button disabled={saving || !form.title.trim() || !form.description.trim()} onClick={save} className="primary-button"><Check size={15} />{saving ? '保存中' : '保存'}</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
