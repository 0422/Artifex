import { Plus, Trash2 } from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'
import { useEffect, useState } from 'react'
import { format } from 'date-fns'

import ConfirmDialog from './ConfirmDialog'
import { newsApi } from '../services/api'
import { useDialogExit } from '../lib/useDialogExit'
import { toast } from '../stores/toastStore'
import { NEWS_DOMAIN_LABELS, type NewsDomain, type NewsSource } from '../lib/types'

// 2026-10-03 新增世势洞察（M6）来源管理弹窗：列表 + 启停 + 新增/编辑 + 删除确认。
// 与 LlmSelectDialog 同属 Radix Dialog + useDialogExit 的既有弹窗范式。
const DOMAIN_OPTIONS = Object.entries(NEWS_DOMAIN_LABELS) as Array<[NewsDomain, string]>

const EMPTY_FORM = { name: '', url: '', domain: 'ai' as NewsDomain }

function formatDateTime(value: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : format(date, 'MM-dd HH:mm')
}

export default function NewsSourcesDialog({ onClose }: { onClose: () => void }) {
  const { open, close } = useDialogExit(onClose)
  const [sources, setSources] = useState<NewsSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  // editing: 'new' 新增表单；NewsSource 编辑该行；null 收起表单
  const [editing, setEditing] = useState<NewsSource | 'new' | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [confirmId, setConfirmId] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    newsApi
      .sources()
      .then(setSources)
      .catch(() => setError('来源加载失败，请稍后重试'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openNew = () => {
    setEditing('new')
    setForm(EMPTY_FORM)
  }

  const openEdit = (source: NewsSource) => {
    setEditing(source)
    setForm({ name: source.name, url: source.url, domain: source.domain })
  }

  const submit = () => {
    const name = form.name.trim()
    const url = form.url.trim()
    if (!name || !url) {
      toast.error('名称和 URL 都不能为空')
      return
    }
    setSaving(true)
    const request =
      editing === 'new'
        ? newsApi.createSource({ name, url, domain: form.domain })
        : newsApi.updateSource((editing as NewsSource).id, { name, url, domain: form.domain })
    request
      .then(() => {
        toast.ok(editing === 'new' ? '来源已添加' : '来源已更新')
        setEditing(null)
        load()
      })
      .catch(() => toast.error('保存失败，请检查 URL 是否可访问'))
      .finally(() => setSaving(false))
  }

  const toggle = (source: NewsSource) => {
    newsApi
      .updateSource(source.id, { is_enabled: !source.is_enabled })
      .then(load)
      .catch(() => toast.error('操作失败，请稍后重试'))
  }

  const remove = (id: string) => {
    newsApi
      .removeSource(id)
      .then(() => {
        toast.ok('来源已删除')
        load()
      })
      .catch(() => toast.error('删除失败，请稍后重试'))
  }

  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) close() }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[70] bg-black/70 data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
        <Dialog.Content className="fixed inset-0 z-[70] flex justify-end data-[state=open]:animate-slide-in-right data-[state=closed]:animate-slide-out-right">
          <div className="panel flex h-full w-full max-w-lg flex-col rounded-none border-y-0 border-r-0">
            <header className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
              <Dialog.Title className="font-semibold text-zinc-100">来源管理</Dialog.Title>
              <div className="flex items-center gap-2">
                <button type="button" className="secondary-button" onClick={openNew}>
                  <Plus size={15} />
                  新增来源
                </button>
                <button type="button" className="icon-button" aria-label="关闭" onClick={close}>
                  ✕
                </button>
              </div>
            </header>

            <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-5">
              {error && <p className="text-xs text-red-300">{error}</p>}

              {editing !== null && (
                <div className="space-y-3 rounded-md border border-zinc-700 bg-zinc-950 p-4">
                  <p className="text-sm font-medium text-zinc-200">
                    {editing === 'new' ? '新增来源' : '编辑来源'}
                  </p>
                  <label className="block space-y-1">
                    <span className="text-xs text-zinc-400">名称</span>
                    <input
                      className="field"
                      value={form.name}
                      maxLength={100}
                      onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                      placeholder="如：MIT Technology Review"
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-xs text-zinc-400">RSS / Atom 地址</span>
                    <input
                      className="field"
                      value={form.url}
                      maxLength={500}
                      onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
                      placeholder="https://example.com/feed"
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-xs text-zinc-400">板块</span>
                    <select
                      className="field"
                      value={form.domain}
                      onChange={(e) => setForm((f) => ({ ...f, domain: e.target.value as NewsDomain }))}
                    >
                      {DOMAIN_OPTIONS.map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="flex justify-end gap-2">
                    <button type="button" className="secondary-button" onClick={() => setEditing(null)}>
                      取消
                    </button>
                    <button type="button" className="primary-button" disabled={saving} onClick={submit}>
                      {saving ? '保存中…' : '保存'}
                    </button>
                  </div>
                </div>
              )}

              {loading ? (
                <p className="text-sm text-zinc-500">加载中…</p>
              ) : sources.length === 0 ? (
                <p className="text-sm text-zinc-500">还没有来源，点右上角「新增来源」添加。</p>
              ) : (
                <ul className="space-y-2">
                  {sources.map((source) => {
                    const fetched = formatDateTime(source.last_fetched_at)
                    return (
                      <li key={source.id} className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
                        <div className="flex items-center gap-2">
                          <span className="rounded border border-zinc-700 px-1.5 py-0.5 text-[11px] text-zinc-400">
                            {NEWS_DOMAIN_LABELS[source.domain]}
                          </span>
                          <span className="min-w-0 flex-1 truncate text-sm text-zinc-100">
                            {source.name}
                          </span>
                          <button
                            type="button"
                            className="text-xs text-zinc-400 hover:text-zinc-100"
                            onClick={() => toggle(source)}
                          >
                            {source.is_enabled ? '停用' : '启用'}
                          </button>
                          <button
                            type="button"
                            className="text-xs text-zinc-400 hover:text-zinc-100"
                            onClick={() => openEdit(source)}
                          >
                            编辑
                          </button>
                          <button
                            type="button"
                            aria-label={`删除 ${source.name}`}
                            className="icon-button h-7 w-7 text-zinc-500 hover:text-red-300"
                            onClick={() => setConfirmId(source.id)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                        <p className="mt-1 truncate text-[11px] text-zinc-500" title={source.url}>
                          {source.url}
                        </p>
                        <p className="mt-0.5 text-[11px] text-zinc-500">
                          {source.is_enabled ? '已启用' : '已停用'}
                          {fetched ? ` · 抓取于 ${fetched}` : ' · 尚未抓取'}
                          {source.last_error ? ` · ${source.last_error}` : ''}
                        </p>
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>

      {confirmId !== null && (
        <ConfirmDialog
          title="删除新闻源"
          message={`删除后该源抓取到的文章与日报素材都会移除，此操作不可恢复。\n源：${sources.find((s) => s.id === confirmId)?.name ?? ''}`}
          onConfirm={() => {
            const id = confirmId
            setConfirmId(null)
            void remove(id)
          }}
          onCancel={() => setConfirmId(null)}
        />
      )}
    </Dialog.Root>
  )
}
