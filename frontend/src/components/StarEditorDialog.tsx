import { useEffect, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Star } from 'lucide-react'

import type { Star as StarModel, StarInput } from '../lib/types'
import { useDialogExit } from '../lib/useDialogExit'

// 2026-10-03 新增摘星阁（M7）新建/编辑弹窗。
//
// 与别处表单的差异只有一个：【Ctrl/Cmd+Enter 直接提交】。写念头最忌仪式感，
// 用户写完之后手不离键盘就能收录；鼠标路径是可选的后备而不是唯一入口。
// 正文区给 5000 字上限并在接近上限时才显示计数——平时不拿数字烦人。

const MAX_CONTENT = 5000

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs text-zinc-400">{label}</span>
      {children}
    </label>
  )
}

export interface StarEditorDialogProps {
  /** 传入即编辑，省略即新建 */
  star?: StarModel | null
  /** 新建时的初始正文（由页面顶部的输入框带过来，避免用户重打一遍） */
  initialContent?: string
  /** 标签补全候选 */
  knownTags?: string[]
  onClose: () => void
  onSave: (input: StarInput) => Promise<void>
}

export default function StarEditorDialog({
  star = null,
  initialContent = '',
  knownTags = [],
  onClose,
  onSave,
}: StarEditorDialogProps) {
  const { open, close } = useDialogExit(onClose)
  const [content, setContent] = useState(star?.content ?? initialContent)
  const [tags, setTags] = useState((star?.tags ?? []).join(' '))
  const [favorite, setFavorite] = useState(star?.is_favorite ?? false)
  const [pinned, setPinned] = useState(star?.is_pinned ?? false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // 打开即聚焦正文区：新建流程省掉一次点击
  useEffect(() => {
    if (!open) return
    const timer = window.setTimeout(() => document.getElementById('star-content')?.focus(), 60)
    return () => window.clearTimeout(timer)
  }, [open])

  const trimmed = content.trim()
  const tooLong = content.length > MAX_CONTENT
  const canSave = trimmed.length > 0 && !tooLong && !saving

  const submit = async () => {
    if (!canSave) return
    setSaving(true)
    setError('')
    try {
      // 标签用空格分隔：中文输入法下切英文逗号要按一次 shift，空格最省事
      await onSave({
        content: trimmed,
        tags: tags.split(/[\s,，]+/).filter(Boolean),
        is_favorite: favorite,
        is_pinned: pinned,
      })
      close()
    } catch {
      setError('保存失败，请稍后重试')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={(next) => !next && close()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[70] bg-black/70 data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
        <Dialog.Content
          className="fixed inset-0 z-[70] flex items-center justify-center p-4 data-[state=open]:animate-dialog-in data-[state=closed]:animate-dialog-out"
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
              event.preventDefault()
              void submit()
            }
          }}
        >
          <div className="w-full max-w-lg rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl">
            <header className="flex items-center gap-2 border-b border-zinc-800 p-4">
              <Star size={15} className="text-teal-400" />
              <Dialog.Title className="text-sm font-semibold text-zinc-100">
                {star ? '修改这颗星' : '摘一颗新星'}
              </Dialog.Title>
            </header>

            <div className="space-y-4 p-5">
              <Field label="这一念">
                <textarea
                  id="star-content"
                  value={content}
                  onChange={(event) => setContent(event.target.value)}
                  rows={6}
                  placeholder="一句没头没尾的话、半截想法、要记下的备忘……不用整理，先记下来。"
                  className="field resize-y leading-6"
                />
              </Field>

              <div className="flex items-end justify-between gap-3">
                <Field label="标签（空格分隔，可选）">
                  <input
                    value={tags}
                    onChange={(event) => setTags(event.target.value)}
                    placeholder="灵感 英语 待读"
                    className="field"
                  />
                </Field>
                {/* 接近上限才显形：平时不拿字数烦人，但要在戳爆上限前提醒 */}
                {content.length > MAX_CONTENT - 500 && (
                  <span
                    className={`shrink-0 pb-2 text-[11px] ${
                      tooLong ? 'text-red-300' : 'text-zinc-500'
                    }`}
                  >
                    {content.length} / {MAX_CONTENT}
                  </span>
                )}
              </div>

              {knownTags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {knownTags.slice(0, 8).map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() =>
                        setTags((current) =>
                          current.split(/[\s,，]+/).includes(tag)
                            ? current
                            : `${current.trim()} ${tag}`.trim(),
                        )
                      }
                      className="rounded-md border border-zinc-700 bg-zinc-950 px-1.5 py-0.5 text-[11px] text-zinc-400 transition-colors hover:border-teal-600 hover:text-teal-300"
                    >
                      + {tag}
                    </button>
                  ))}
                </div>
              )}

              <div className="flex flex-wrap gap-4 text-xs text-zinc-400">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={favorite}
                    onChange={(event) => setFavorite(event.target.checked)}
                    className="accent-teal-500"
                  />
                  收藏（金色常亮）
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={pinned}
                    onChange={(event) => setPinned(event.target.checked)}
                    className="accent-teal-500"
                  />
                  钉在夜空顶端
                </label>
              </div>

              {error && <p className="text-xs text-red-300">{error}</p>}
            </div>

            <footer className="flex items-center gap-2 border-t border-zinc-800 p-4">
              <span className="mr-auto text-[11px] text-zinc-500">
                <kbd className="rounded border border-zinc-700 px-1">Ctrl</kbd>+
                <kbd className="rounded border border-zinc-700 px-1">Enter</kbd> 直接收录
              </span>
              <button type="button" onClick={close} className="secondary-button">
                取消
              </button>
              <button
                type="button"
                onClick={() => void submit()}
                disabled={!canSave}
                className="primary-button"
              >
                {saving ? '收录中…' : star ? '保存' : '收录这颗星'}
              </button>
            </footer>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
