import { useState } from 'react'

const titleCase = (value: string) => value.toLowerCase().replace(/\b\p{L}/gu, (letter) => letter.toUpperCase())
const sentenceCase = (value: string) => value.toLowerCase().replace(/(^|[.!?]\s+)(\p{L})/gu, (_, prefix: string, letter: string) => `${prefix}${letter.toUpperCase()}`)

export default function CaseConverterTool() {
  const [text, setText] = useState('')

  const convert = (mode: 'upper' | 'lower' | 'title' | 'sentence') => {
    if (mode === 'upper') setText(text.toUpperCase())
    if (mode === 'lower') setText(text.toLowerCase())
    if (mode === 'title') setText(titleCase(text))
    if (mode === 'sentence') setText(sentenceCase(text))
  }

  return (
    <div>
      <label className="block">
        <span className="mb-2 block text-sm font-medium text-zinc-300">英文文本</span>
        <textarea autoFocus value={text} onChange={(event) => setText(event.target.value)} placeholder="Type or paste English text here..." className="field min-h-[320px] resize-y leading-6" />
      </label>
      <div className="mt-4 flex flex-wrap gap-2">
        <button onClick={() => convert('upper')} className="secondary-button">全部大写</button>
        <button onClick={() => convert('lower')} className="secondary-button">全部小写</button>
        <button onClick={() => convert('title')} className="secondary-button">标题格式</button>
        <button onClick={() => convert('sentence')} className="secondary-button">句首大写</button>
        <button disabled={!text} onClick={() => setText('')} className="secondary-button ml-auto">清空</button>
      </div>
    </div>
  )
}
