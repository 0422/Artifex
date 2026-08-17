import { ArrowLeft, Wrench } from 'lucide-react'
import { Link, Navigate, useParams } from 'react-router-dom'

import { findTool } from '../lib/tools'

export default function ToolPage() {
  const { toolId } = useParams()
  const tool = findTool(toolId)

  if (!tool?.component) return <Navigate to="/tools" replace />

  const Tool = tool.component
  const Icon = tool.icon

  return (
    <div className="min-h-full bg-zinc-900">
      <header className="border-b border-zinc-800 bg-zinc-950/70 px-8 py-5 lg:px-10">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          <Link to="/tools" title="返回工具库" aria-label="返回工具库" className="icon-button"><ArrowLeft size={19} /></Link>
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-teal-900 bg-teal-950/50 text-teal-300"><Icon size={20} /></div>
          <div className="min-w-0"><h1 className="font-semibold text-zinc-100">{tool.name}</h1><p className="mt-0.5 truncate text-xs text-zinc-500">{tool.description}</p></div>
        </div>
      </header>
      <main className="px-8 py-8 lg:px-10">
        <div className="mx-auto max-w-6xl rounded-xl border border-zinc-800 bg-zinc-950/40 p-6">
          <div className="mb-6 flex items-center gap-2 border-b border-zinc-800 pb-4 text-xs text-zinc-500"><Wrench size={14} />所有处理均在当前浏览器中完成</div>
          <Tool />
        </div>
      </main>
    </div>
  )
}
