import { Check, Copy } from 'lucide-react'
import { useMemo, useState } from 'react'

export default function LineDeduplicatorTool() {
  const [text, setText] = useState('')
  const [copied, setCopied] = useState(false)
  const result = useMemo(() => {
    const lines = text.split(/\r?\n/u)
    const unique = [...new Set(lines.filter((line) => line.trim()))]
    return { text: unique.join('\n'), removed: lines.filter((line) => line.trim()).length - unique.length }
  }, [text])

  const copy = async () => {
    if (!result.text) return
    await navigator.clipboard.writeText(result.text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <label className="block">
        <span className="mb-2 block text-sm font-medium text-zinc-300">原始内容</span>
        <textarea autoFocus value={text} onChange={(event) => setText(event.target.value)} placeholder="每行输入一个词语或句子..." className="field min-h-[360px] resize-y leading-6" />
      </label>
      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-zinc-300">去重结果</span>
          <span className="text-xs text-zinc-500">已移除 {result.removed} 个重复项</span>
        </div>
        <textarea readOnly value={result.text} placeholder="结果会显示在这里" className="field min-h-[360px] resize-y leading-6" />
        <button disabled={!result.text} onClick={copy} className="secondary-button mt-3">
          {copied ? <Check size={15} /> : <Copy size={15} />}{copied ? '已复制' : '复制结果'}
        </button>
      </div>
    </div>
  )
}
