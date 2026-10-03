import { useEffect, useState } from 'react'
import { Check, Loader2, Pencil, Plus, Trash2, X } from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'

import { llmApi } from '../services/api'
import type { LLMModel, LLMProvider } from '../lib/types'
// 2026-10-02 收尾轮：关闭先播退场动画再卸载
import { useDialogExit } from '../lib/useDialogExit'

/**
 * 2026-10-01 LLM Select 弹窗。
 *
 * 多家 LLM 的请求地址 / API Key / 模型集中在后端配置文件中，这里负责：
 *   1. 展示所有供应商及其模型，标出当前生效项
 *   2. 点击模型即切换（顺带激活所属供应商）
 *   3. 每个条目都可编辑保存（名称/地址/Key/模型，API Key 留空表示不改）
 *   4. 新增供应商与模型，写入成功后重新拉取列表
 */

type Banner = { kind: 'error' | 'ok'; text: string } | null
type EditForm = { name: string; base_url: string; api_key: string; models: LLMModel[] }
type Draft = { adding: boolean; addForm: typeof EMPTY_ADD; editingId: string | null; editForm: EditForm }

const splitModels = (raw: string) =>
  raw
    .split(/[\n,，]/)
    .map((s) => s.trim())
    .filter(Boolean)

const emptyForm = (): EditForm => ({ name: '', base_url: '', api_key: '', models: [] })
const EMPTY_ADD = { name: '', base_url: '', api_key: '', models: '' }
const DRAFT_KEY = 'artifex_llm_dialog_draft'

const readDraft = (): Draft | null => {
  try {
    const raw = localStorage.getItem(DRAFT_KEY)
    return raw ? (JSON.parse(raw) as Draft) : null
  } catch {
    return null
  }
}

export default function LlmSelectDialog({ onClose }: { onClose: () => void }) {
  const [providers, setProviders] = useState<LLMProvider[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [activeModel, setActiveModel] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [banner, setBanner] = useState<Banner>(null)

  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState(EMPTY_ADD)

  // 正在编辑的供应商 id 及其表单；同一时间只编辑一个条目
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<EditForm>(emptyForm)
  // 已经因为"有未保存修改"提示过一次；再点一次关闭才真正关，避免误触丢内容
  const [warned, setWarned] = useState(false)

  // ---- 草稿：填到一半被关掉也不丢，重开弹窗自动恢复 ----
  useEffect(() => {
    const draft = readDraft()
    if (!draft) return
    setAdding(draft.adding)
    setForm(draft.addForm ?? EMPTY_ADD)
    setEditingId(draft.editingId)
    setEditForm(draft.editForm ?? emptyForm())
    setBanner({ kind: 'ok', text: '已恢复上次填到一半的内容，可继续编辑。' })
  }, [])

  useEffect(() => {
    const draft: Draft = { adding, addForm: form, editingId, editForm }
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
    } catch {
      // 隐私模式下 localStorage 可能不可写，忽略即可
    }
  }, [adding, form, editingId, editForm])

  const clearDraft = () => {
    try {
      localStorage.removeItem(DRAFT_KEY)
    } catch {
      /* 忽略 */
    }
  }

  const hasDraft = () => {
    if (adding) return !!(form.name.trim() || form.base_url.trim() || form.api_key.trim() || form.models.trim())
    if (!editingId) return false
    const provider = providers.find((p) => p.id === editingId)
    if (!provider) return !!editForm.name.trim() || !!editForm.base_url.trim() || !!editForm.api_key.trim()
    return (
      editForm.name !== provider.name ||
      editForm.base_url !== provider.base_url ||
      !!editForm.api_key.trim() ||
      JSON.stringify(editForm.models) !== JSON.stringify(provider.models)
    )
  }

  /**
   * 统一的关闭入口。有未保存修改时先提示、不关闭，再点一次才放行——
   * 遮罩误点、误触 Esc、滚动误判都不该让填了一半的表单消失。
   *
   * 2026-10-02 收尾轮：真正关闭改走 useDialogExit 的 close()（先播退场动画
   * 再回调卸载），clearDraft 挪到退场结束后的回调里执行
   */
  const { open, close } = useDialogExit(() => {
    clearDraft()
    onClose()
  })
  const requestClose = () => {
    if (hasDraft() && !warned) {
      setWarned(true)
      setBanner({ kind: 'error', text: '有未保存的修改。请点「保存」或「取消」；若确认放弃，请再点一次关闭。' })
      return
    }
    close()
  }

  // 2026-10-02 第二批：原 document 级 keydown 监听已删除，Esc 逻辑移到
  // Radix Dialog 的 onEscapeKeyDown（保留原来的中文输入法选词保护与未保存提示），
  // 另外白拿焦点陷阱、焦点归还、背景滚动锁和出入场动画

  const load = async () => {
    try {
      const data = await llmApi.list()
      setProviders(data.providers)
      setActiveId(data.active_provider_id)
      setActiveModel(data.active_model)
    } catch {
      setBanner({ kind: 'error', text: '加载 LLM 列表失败，请重试' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const apply = async (
    action: () => Promise<{ active_provider_id: string | null; active_model: string | null; providers: LLMProvider[] }>,
  ) => {
    setBusy(true)
    setBanner(null)
    try {
      const data = await action()
      // 写入成功后刷新列表，让新增/修改/切换立即反映在界面上
      setProviders(data.providers)
      setActiveId(data.active_provider_id)
      setActiveModel(data.active_model)
      return true
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setBanner({ kind: 'error', text: detail ?? '操作失败，请重试' })
      return false
    } finally {
      setBusy(false)
    }
  }

  const activate = (provider: LLMProvider, model?: string) =>
    apply(() => llmApi.activate(provider.id, model))

  const submitAdd = async () => {
    const models = splitModels(form.models)
    if (!form.name.trim() || !form.base_url.trim() || !form.api_key.trim() || !models.length) {
      setBanner({ kind: 'error', text: '名称、请求地址、API Key、模型均为必填' })
      return
    }
    const ok = await apply(() =>
      llmApi.create({ name: form.name.trim(), base_url: form.base_url.trim(), api_key: form.api_key.trim(), models }),
    )
    if (ok) {
      setForm(EMPTY_ADD)
      setAdding(false)
      // 已落库，草稿就没有保留价值了，避免下次打开弹窗又弹出旧内容
      clearDraft()
      setWarned(false)
    }
  }

  const startEdit = (provider: LLMProvider) => {
    setEditingId(provider.id)
    // Key 一律从空开始：留空即不修改，避免误清空已保存的 Key
    setEditForm({
      name: provider.name,
      base_url: provider.base_url,
      api_key: '',
      models: provider.models.map((m) => ({ ...m })),
    })
    setBanner(null)
    setWarned(false)
  }

  const submitEdit = async () => {
    if (!editingId) return
    const models = editForm.models
      .map((m) => ({ name: m.name.trim(), json_mode: m.json_mode }))
      .filter((m) => m.name)
    if (!editForm.name.trim() || !editForm.base_url.trim() || !models.length) {
      setBanner({ kind: 'error', text: '名称、请求地址、模型均为必填' })
      return
    }
    const ok = await apply(() =>
      llmApi.update(editingId, {
        name: editForm.name.trim(),
        base_url: editForm.base_url.trim(),
        api_key: editForm.api_key.trim() || undefined,
        models,
      }),
    )
    if (ok) {
      setEditingId(null)
      // 保存成功：草稿已无用，清掉并复位"已提示"状态
      clearDraft()
      setWarned(false)
    }
  }

  const remove = (provider: LLMProvider) => apply(() => llmApi.remove(provider.id))

  const patchModel = (index: number, patch: Partial<LLMModel>) =>
    setEditForm((f) => ({ ...f, models: f.models.map((m, i) => (i === index ? { ...m, ...patch } : m)) }))

  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) requestClose() }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[80] bg-black/70 data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
        <Dialog.Content
          className="fixed inset-0 z-[80] flex items-center justify-center p-4 data-[state=open]:animate-dialog-in data-[state=closed]:animate-dialog-out"
          // 点遮罩等同点关闭：同样先过 requestClose 的未保存检查，不会误关
          onInteractOutside={(event) => {
            event.preventDefault()
            requestClose()
          }}
          onEscapeKeyDown={(event) => {
            // 中文输入法选词也会派发 Escape：正在填表单时一律不关，并拦住 Radix 的默认关闭
            const el = event.target as HTMLElement | null
            const typing = !!el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)
            if (typing) {
              event.preventDefault()
              return
            }
            // 有未保存修改：也拦住默认关闭，改为弹提示，再按一次才放行（requestClose 内部判断）
            if (hasDraft() && !warned) event.preventDefault()
            requestClose()
          }}
        >
          <div className="w-full max-w-2xl rounded-xl border border-zinc-700 bg-zinc-900 shadow-2xl">
            <header className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
              <div>
                <Dialog.Title className="font-semibold text-zinc-100">LLM Select</Dialog.Title>
                <Dialog.Description className="mt-0.5 text-xs text-zinc-400">切换、修改或新增 LLM 供应商，立即生效，无需重启</Dialog.Description>
              </div>
              <button title="关闭" aria-label="关闭" onClick={requestClose} className="icon-button">
                <X size={18} />
              </button>
            </header>

        <div className="max-h-[60vh] space-y-3 overflow-auto p-5">
          {banner && (
            <p className={`rounded-md px-3 py-2 text-xs ${banner.kind === 'error' ? 'bg-red-950/60 text-red-300' : 'bg-emerald-950/60 text-emerald-300'}`}>
              {banner.text}
            </p>
          )}

          {loading ? (
            <p className="flex items-center gap-2 py-8 text-sm text-zinc-400">
              <Loader2 size={15} className="animate-spin" />加载中...
            </p>
          ) : (
            providers.map((provider) => {
              const isActive = provider.id === activeId
              const editing = provider.id === editingId

              if (editing) {
                return (
                  <div key={provider.id} className="rounded-lg border border-teal-700 bg-zinc-950/60 p-4">
                    <h3 className="text-sm font-medium text-zinc-100">编辑：{provider.name}</h3>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <label className="block">
                        <span className="mb-1 block text-xs text-zinc-400">名称</span>
                        <input
                          value={editForm.name}
                          onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                          className="field"
                        />
                      </label>
                      <label className="block">
                        <span className="mb-1 block text-xs text-zinc-400">请求地址</span>
                        <input
                          value={editForm.base_url}
                          onChange={(e) => setEditForm((f) => ({ ...f, base_url: e.target.value }))}
                          placeholder="https://api.deepseek.com"
                          className="field font-mono"
                        />
                      </label>
                      <label className="block sm:col-span-2">
                        <span className="mb-1 block text-xs text-zinc-400">
                          API Key
                          <span className="ml-1 text-zinc-400">（留空表示不修改，当前 {provider.api_key_masked || '未填写'}）</span>
                        </span>
                        <input
                          value={editForm.api_key}
                          onChange={(e) => setEditForm((f) => ({ ...f, api_key: e.target.value }))}
                          placeholder="sk-..."
                          className="field font-mono"
                        />
                      </label>
                    </div>

                    {/* 模型逐行编辑：可改名、可单独开关 JSON 输出、可移除 */}
                    <div className="mt-3">
                      <span className="mb-1 block text-xs text-zinc-400">模型</span>
                      <div className="space-y-2">
                        {editForm.models.map((model, index) => (
                          <div key={index} className="flex items-center gap-2">
                            <input
                              value={model.name}
                              onChange={(e) => patchModel(index, { name: e.target.value })}
                              placeholder="模型名"
                              className="field flex-1 font-mono"
                            />
                            <label
                              className="flex shrink-0 items-center gap-1.5 text-xs text-zinc-400"
                              title="要求模型返回 JSON；思考类模型（如 deepseek-reasoner）不支持，需取消勾选"
                            >
                              <input
                                type="checkbox"
                                checked={model.json_mode}
                                onChange={(e) => patchModel(index, { json_mode: e.target.checked })}
                                className="accent-teal-600"
                              />
                              JSON
                            </label>
                            <button
                              title="移除该模型"
                              aria-label={`移除 ${model.name}`}
                              disabled={busy}
                              onClick={() => setEditForm((f) => ({ ...f, models: f.models.filter((_, i) => i !== index) }))}
                              className="icon-button hover:text-red-300"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        ))}
                      </div>
                      <button
                        onClick={() => setEditForm((f) => ({ ...f, models: [...f.models, { name: '', json_mode: true }] }))}
                        className="secondary-button mt-2 h-8 text-xs"
                      >
                        <Plus size={13} />添加模型
                      </button>
                    </div>

                    <div className="mt-4 flex justify-end gap-2">
                      <button
                        onClick={() => {
                          setEditingId(null)
                          clearDraft()
                          setWarned(false)
                        }}
                        className="secondary-button"
                        disabled={busy}
                      >
                        取消
                      </button>
                      <button onClick={submitEdit} className="primary-button" disabled={busy}>
                        {busy ? '保存中...' : '保存'}
                      </button>
                    </div>
                  </div>
                )
              }

              return (
                <div
                  key={provider.id}
                  className={`rounded-lg border p-4 transition-colors ${isActive ? 'border-teal-700 bg-teal-950/20' : 'border-zinc-800 bg-zinc-950/40'}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="truncate text-sm font-medium text-zinc-100">{provider.name}</h3>
                        {provider.builtin && (
                          <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">内置</span>
                        )}
                        {isActive && (
                          <span className="flex items-center gap-1 rounded bg-teal-900/70 px-1.5 py-0.5 text-[10px] text-teal-300">
                            <Check size={10} />当前
                          </span>
                        )}
                      </div>
                      <p className="mt-1 truncate font-mono text-xs text-zinc-400" title={provider.base_url}>
                        {provider.base_url}
                      </p>
                      <p className="mt-0.5 text-[11px] text-zinc-400">
                        API Key：{provider.api_key_masked || '未填写'}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        title="修改"
                        aria-label={`修改 ${provider.name}`}
                        disabled={busy}
                        onClick={() => startEdit(provider)}
                        className="icon-button"
                      >
                        <Pencil size={15} />
                      </button>
                      {!provider.builtin && (
                        <button
                          title="删除"
                          aria-label={`删除 ${provider.name}`}
                          disabled={busy}
                          onClick={() => remove(provider)}
                          className="icon-button hover:text-red-300"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                      {!isActive && (
                        <button
                          disabled={busy}
                          onClick={() => activate(provider)}
                          className="secondary-button h-8 px-3 text-xs"
                        >
                          启用
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 模型标签：点击即选用该模型，非激活供应商会顺带被激活 */}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {provider.models.length === 0 && <span className="text-xs text-zinc-400">暂无模型</span>}
                    {provider.models.map((model) => {
                      const selected = isActive && model.name === activeModel
                      return (
                        <button
                          key={model.name}
                          disabled={busy}
                          onClick={() => activate(provider, model.name)}
                          title={model.json_mode ? undefined : '该模型不支持 JSON 输出，已自动关闭 json_mode'}
                          className={`flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs transition-colors disabled:opacity-50 ${
                            selected
                              ? 'border-teal-600 bg-teal-900/40 text-teal-200'
                              : 'border-zinc-700 bg-zinc-900 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200'
                          }`}
                        >
                          {model.name}
                          {!model.json_mode && <span className="text-[10px] text-amber-500">无JSON</span>}
                          {selected && <Check size={11} />}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )
            })
          )}

          {/* 新增供应商表单 */}
          {adding ? (
            <div className="rounded-lg border border-zinc-700 bg-zinc-950/60 p-4">
              <h3 className="text-sm font-medium text-zinc-100">新增 LLM</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1 block text-xs text-zinc-400">名称</span>
                  <input
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="例如：DeepSeek 官方"
                    className="field"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-zinc-400">请求地址</span>
                  <input
                    value={form.base_url}
                    onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))}
                    placeholder="https://api.deepseek.com"
                    className="field font-mono"
                  />
                </label>
                <label className="block sm:col-span-2">
                  <span className="mb-1 block text-xs text-zinc-400">API Key</span>
                  <input
                    value={form.api_key}
                    onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                    placeholder="sk-..."
                    className="field font-mono"
                  />
                </label>
                <label className="block sm:col-span-2">
                  <span className="mb-1 block text-xs text-zinc-400">
                    模型（每行一个，或用逗号分隔）
                    <span className="ml-1 text-zinc-400">默认开启 JSON 输出，如需关闭请在保存后点「修改」逐模型调整</span>
                  </span>
                  <textarea
                    value={form.models}
                    onChange={(e) => setForm((f) => ({ ...f, models: e.target.value }))}
                    placeholder={'deepseek-chat\ndeepseek-reasoner'}
                    className="field min-h-20 resize-y font-mono"
                  />
                </label>
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <button
                  onClick={() => {
                    setAdding(false)
                    clearDraft()
                    setWarned(false)
                  }}
                  className="secondary-button"
                  disabled={busy}
                >
                  取消
                </button>
                <button onClick={submitAdd} className="primary-button" disabled={busy}>
                  {busy ? '提交中...' : '保存并刷新列表'}
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setAdding(true)}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-zinc-700 py-3 text-sm text-zinc-400 transition-colors hover:border-teal-700 hover:text-teal-300"
            >
              <Plus size={15} />新增 LLM
            </button>
          )}
        </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
