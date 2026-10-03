import { useEffect, useState } from 'react'
import { Check, ListPlus, Pencil, Plus, Sparkles, Trash2, X } from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'

import { scenarioApi } from '../services/api'
import type { Scenario, ScenarioInput, ScenarioLanguage } from '../lib/types'
// 2026-10-02 收尾轮：编辑弹窗关闭先播退场动画再卸载
import { useDialogExit } from '../lib/useDialogExit'

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
  const [loading, setLoading] = useState(Boolean(requestedId))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  // 2026-09-30 两种形态：
  //   placeholder — 初始状态，不请求也不展示任何场景卡片。
  //                这块区域预留给学情分析上线后展示"需要重复练习的场景"。
  //   browse     — 用户点「浏览场景」后才拉取知识库场景列表供选择。
  // 带 ?scenario=xxx 从知识库跳转过来时直接进 browse 并选中那一个。
  const [mode, setMode] = useState<'placeholder' | 'browse'>(requestedId ? 'browse' : 'placeholder')

  // 2026-10-02 收尾轮：编辑弹窗退场动画。hook 必须在组件顶层无条件调用
  // （弹窗 JSX 在下面 {editing && ...} 条件块里，close 在块内使用）。
  // reopen 不可省：关闭后 open 停在 false，下次打开编辑器必须 reset，
  // 否则 Dialog.Root 渲染不出内容（详见 useDialogExit 注释）
  const { open: editorOpen, close: closeEditor, reopen: reopenEditor } = useDialogExit(() => setEditing(null))

  useEffect(() => {
    // effect 里不做同步 setState：loading 的置 true 由 openBrowser（事件处理器）
    // 或初始状态负责，这里只在请求结束后收尾
    if (mode !== 'browse') return
    scenarioApi.list().then((data) => {
      setItems(data)
      // 只在被明确请求时才预选中；否则保持空选择，由用户自己挑
      if (!selectedId && requestedId) {
        const requested = data.find((item) => item.id === requestedId)
        if (requested) onSelect(requested)
      }
    }).catch(() => setError('场景加载失败')).finally(() => setLoading(false))
  }, [mode]) // eslint-disable-line react-hooks/exhaustive-deps

  const openBrowser = () => {
    setError('')
    setMode('browse')
    setLoading(true)
  }

  const openEditor = (item?: Scenario) => {
    setError('')
    // 2026-10-02 收尾轮：先 reset 退场动画状态再打开，防止上次关闭留下的 open=false
    // 让这次 Dialog.Root 渲染不出内容
    reopenEditor()
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
      // 2026-09-30 建完切到 browse：placeholder 形态下列表是空的，
      // 不切的话新建的场景创建了却看不见
      setMode('browse')
      setItems((current) => editing === 'new'
        ? [...current, saved]
        : current.map((item) => item.id === saved.id ? saved : item))
      onSelect(saved)
      // 2026-10-02 收尾轮：保存成功后也走退场动画关闭（组件级 closeEditor，
      // 见顶部 useDialogExit），而不是直接 setEditing(null) 瞬时消失
      closeEditor()
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
    // 2026-10-02 全卡片式改版：场景面板由「通栏 + 右侧竖线」改为独立面板。
    // 原 className：flex h-full min-h-0 flex-col border-r border-zinc-800 bg-zinc-950，边框/底色改由 panel 类提供
    <section className="panel flex h-full min-h-0 flex-col">
      <div className="flex h-14 items-center justify-between border-b border-zinc-800 px-4">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100">练习场景</h2>
          <p className="text-xs text-zinc-400">{mode === 'browse' ? '选择一个情境开始对话' : '暂无待练习场景'}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {mode === 'placeholder' && (
            <button title="浏览场景" disabled={disabled} onClick={openBrowser} className="secondary-button h-8 px-2.5 text-xs">
              <ListPlus size={15} />浏览场景
            </button>
          )}
          <button title="新建场景" disabled={disabled} onClick={() => openEditor()} className="icon-button">
            <Plus size={17} />
          </button>
          {onClose && <span className="lg:hidden"><button title="收起场景" aria-label="收起场景" onClick={onClose} className="icon-button"><X size={17} /></button></span>}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {mode === 'placeholder' && (
          // 2026-10-02 第三批：占位状态从「裸图标+两行字」升级为与共享 EmptyState 同一套语言
          // （图标置于 1px 细环 + teal 模糊光晕中），等学情分析上线前这块区域也有品牌质感
          <div className="flex flex-col items-center px-3 py-10 text-center">
            <span className="relative flex h-14 w-14 items-center justify-center">
              <span className="absolute inset-0 rounded-full ring-1 ring-inset ring-zinc-800" />
              <span className="absolute inset-3 rounded-full bg-teal-500/10 blur-[8px]" />
              <Sparkles className="relative text-zinc-500" size={22} strokeWidth={1.5} />
            </span>
            <p className="mt-4 text-sm text-zinc-300">暂无待练习场景</p>
            <p className="mt-1.5 text-xs leading-5 text-zinc-400">
              学情分析上线后，这里会列出需要重复练习的场景。
            </p>
          </div>
        )}
        {mode === 'browse' && (
          <>
            {/* 2026-10-02 第二批：列表加载态由"正在加载场景..."纯文字换成骨架屏，
                结构与真实卡片一致（徽章行 + 标题 + 两行说明），避免加载完成后的布局跳动 */}
            {loading && (
              <div className="space-y-1" aria-busy="true" aria-label="正在加载场景">
                {[0, 1, 2, 3].map((row) => (
                  <div key={row} className="rounded-md border border-transparent px-3 py-3">
                    <div className="flex items-center gap-2">
                      <div className="skeleton h-5 w-16" />
                      <div className="skeleton ml-auto h-4 w-10" />
                    </div>
                    <div className="skeleton mt-2.5 h-4 w-2/5" />
                    <div className="skeleton mt-2 h-3 w-full" />
                    <div className="skeleton mt-1.5 h-3 w-3/5" />
                  </div>
                ))}
              </div>
            )}
            {!loading && items.length === 0 && <p className="p-3 text-sm text-zinc-400">还没有可用场景</p>}
            {items.map((item) => (
              <div key={item.id} className={`group mb-1 flex items-start gap-2 rounded-md border px-3 py-3 ${selectedId === item.id ? 'border-teal-700 bg-teal-950/40' : 'border-transparent hover:bg-zinc-800'}`}>
                <button disabled={disabled} onClick={() => onSelect(item)} className="min-w-0 flex-1 text-left">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-zinc-100">{item.title}</span>
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">{item.difficulty}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-xs leading-5 text-zinc-400">{item.description}</p>
                </button>
                {!disabled && (
                  <div className="hidden shrink-0 gap-1 group-hover:flex">
                    <button title="编辑" onClick={() => openEditor(item)} className="icon-button h-7 w-7"><Pencil size={13} /></button>
                    <button title="停用" onClick={() => remove(item)} className="icon-button h-7 w-7 hover:text-red-400"><Trash2 size={13} /></button>
                  </div>
                )}
              </div>
            ))}
          </>
        )}
      </div>
      {error && <p className="border-t border-zinc-800 px-4 py-2 text-xs text-red-400">{error}</p>}

      {/* 2026-10-02 第二批：编辑弹窗迁移到 Radix Dialog。
          原先是手写 div（role=dialog 但无 Esc、无焦点陷阱、不锁滚动、无动画） */}
      {editing && (
        <Dialog.Root open={editorOpen} onOpenChange={(open) => { if (!open) closeEditor() }}>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 z-[70] bg-black/70 data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
            <Dialog.Content className="fixed inset-0 z-[70] flex items-center justify-center p-4 data-[state=open]:animate-dialog-in data-[state=closed]:animate-dialog-out">
              <div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl">
                <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
                  <Dialog.Title className="font-semibold text-zinc-100">{editing === 'new' ? '新建练习场景' : '编辑练习场景'}</Dialog.Title>
                  <button title="关闭" onClick={closeEditor} className="icon-button"><X size={17} /></button>
                </div>
                <Dialog.Description className="sr-only">填写场景名称与情境说明，保存后即可用于对话练习。</Dialog.Description>
                <div className="space-y-4 p-5">
              <label className="block text-sm text-zinc-300">场景名称
                <input autoFocus value={form.title} maxLength={100} onChange={(e) => setForm({ ...form, title: e.target.value })} className="field mt-1.5" placeholder="例如：在咖啡店点单" />
              </label>
              <label className="block text-sm text-zinc-300">情境说明
                <textarea value={form.description} maxLength={2000} onChange={(e) => setForm({ ...form, description: e.target.value })} className="field mt-1.5 min-h-28 resize-y" placeholder="说明角色、目标和对话背景" />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block text-sm text-zinc-300">语言
                  <select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value as ScenarioLanguage })} className="field mt-1.5">
                    <option value="ja">日语</option><option value="en">英语</option><option value="zh">中文</option>
                  </select>
                </label>
                {/* 2026-09-30 难度改为不选：由后端按语言取默认值（en→B1 / ja→N4 / zh→intermediate） */}
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-zinc-800 px-5 py-4">
              <button onClick={closeEditor} className="secondary-button"><X size={15} />取消</button>
              <button disabled={saving || !form.title.trim() || !form.description.trim()} onClick={save} className="primary-button"><Check size={15} />{saving ? '保存中' : '保存'}</button>
            </div>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      )}
    </section>
  )
}
