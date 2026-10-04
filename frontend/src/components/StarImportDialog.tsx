import { useMemo, useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { Upload } from 'lucide-react'

import type { StarImportInput } from '../lib/types'
import { useDialogExit } from '../lib/useDialogExit'

// 2026-10-03 新增摘星阁（M7）批量导入弹窗。
//
// 「从别处搬旧备忘录进来」是这个模块的第二个入口：没人愿意在新工具里
// 一颗一颗重打 300 条旧笔记。这里一行一颗星，全程只做本地条数预览，
// 提交一次请求，后端跳过空白行与批次内重复行。

const MAX_LINES = 200

export interface StarImportDialogProps {
  knownTags?: string[]
  onClose: () => void
  onImport: (input: StarImportInput) => Promise<{ created: number; skipped: number }>
}

export default function StarImportDialog({
  knownTags = [],
  onClose,
  onImport,
}: StarImportDialogProps) {
  const { open, close } = useDialogExit(onClose)
  const [text, setText] = useState('')
  const [tags, setTags] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // 条数预览实时算：用户在点提交前就该知道会进来多少颗
  const stats = useMemo(() => {
    const lines = text.split('\n')
    const nonBlank = new Set(lines.map((line) => line.trim()).filter(Boolean))
    return {
      raw: lines.length,
      unique: nonBlank.size,
      skipped: lines.length - nonBlank.size,
      overflow: Math.max(0, nonBlank.size - MAX_LINES),
    }
  }, [text])

  const submit = async () => {
    const lines = text.split('\n').map((line) => line.trim()).filter(Boolean)
    if (lines.length === 0) {
      setError('一行一颗星，先粘点内容进来')
      return
    }
    setBusy(true)
    setError('')
    try {
      const result = await onImport({
        lines: lines.slice(0, MAX_LINES),
        tags: tags.split(/[\s,，]+/).filter(Boolean),
      })
      close()
    } catch {
      setError('导入失败，请稍后重试')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={(next) => !next && close()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[70] bg-black/70 data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
        <Dialog.Content className="fixed inset-0 z-[70] flex items-center justify-center p-4 data-[state=open]:animate-dialog-in data-[state=closed]:animate-dialog-out">
          <div className="w-full max-w-lg rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl">
            <header className="flex items-center gap-2 border-b border-zinc-800 p-4">
              <Upload size={15} className="text-teal-400" />
              <Dialog.Title className="text-sm font-semibold text-zinc-100">搬一批星星过来</Dialog.Title>
            </header>

            <div className="space-y-4 p-5">
              <label className="block">
                <span className="mb-1.5 block text-xs text-zinc-400">一行一颗星</span>
                <textarea
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  rows={10}
                  placeholder={'旧备忘录、笔记软件的导出、随手记下的句子……\n每行一条，空行会被自动跳过。'}
                  className="field resize-y font-mono text-xs leading-6"
                />
              </label>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-zinc-500">
                <span className="text-teal-300">将收录 {stats.unique} 颗</span>
                {stats.skipped > 0 && <span>跳过 {stats.skipped} 行（空行或批次内重复）</span>}
                {stats.overflow > 0 && (
                  <span className="text-amber-300">
                    超出单批 {MAX_LINES} 颗上限，多出的 {stats.overflow} 颗不会收录（可再导一次）
                  </span>
                )}
              </div>

              <label className="block">
                <span className="mb-1.5 block text-xs text-zinc-400">统一标签（可选，空格分隔）</span>
                <input
                  value={tags}
                  onChange={(event) => setTags(event.target.value)}
                  placeholder="旧备忘录"
                  className="field"
                />
              </label>

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

              {error && <p className="text-xs text-red-300">{error}</p>}
            </div>

            <footer className="flex justify-end gap-2 border-t border-zinc-800 p-4">
              <button type="button" onClick={close} className="secondary-button">
                取消
              </button>
              <button
                type="button"
                onClick={() => void submit()}
                disabled={busy || stats.unique === 0}
                className="primary-button"
              >
                {busy ? '收录中…' : `收录 ${stats.unique} 颗`}
              </button>
            </footer>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
