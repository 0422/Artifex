import { useMemo, useState } from 'react'

export default function TextStatisticsTool() {
  const [text, setText] = useState('')
  const statistics = useMemo(() => {
    const trimmed = text.trim()
    return {
      characters: text.length,
      charactersWithoutSpaces: text.replace(/\s/gu, '').length,
      words: trimmed ? trimmed.match(/[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu)?.length ?? 0 : 0,
      lines: text ? text.split(/\r?\n/u).length : 0,
    }
  }, [text])

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
      <label className="block">
        <span className="mb-2 block text-sm font-medium text-zinc-300">待统计文本</span>
        <textarea
          autoFocus
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="在这里输入或粘贴文本..."
          className="field min-h-[360px] resize-y leading-6"
        />
      </label>
      <section className="grid content-start grid-cols-2 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950/50 xl:grid-cols-1">
        <Statistic label="字符数" value={statistics.characters} />
        <Statistic label="字符数（不含空格）" value={statistics.charactersWithoutSpaces} />
        <Statistic label="单词数" value={statistics.words} />
        <Statistic label="行数" value={statistics.lines} />
      </section>
    </div>
  )
}

function Statistic({ label, value }: { label: string; value: number }) {
  return <div className="border-b border-r border-zinc-800 p-5 last:border-b-0 xl:border-r-0"><p className="text-xs text-zinc-500">{label}</p><p className="mt-2 text-2xl font-semibold text-teal-300">{value}</p></div>
}
