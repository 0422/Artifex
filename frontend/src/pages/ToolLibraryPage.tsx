import { ArrowRight, Wrench } from 'lucide-react'
import { Link } from 'react-router-dom'

import { TOOLS } from '../lib/tools'

export default function ToolLibraryPage() {
  return (
    <div className="min-h-full bg-zinc-900 px-8 py-8 lg:px-10">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8">
          <div className="flex items-center gap-2 text-teal-400"><Wrench size={18} /><span className="text-xs font-medium uppercase tracking-wider">Toolkit</span></div>
          <h1 className="mt-3 text-2xl font-semibold text-zinc-100">工具库</h1>
          <p className="mt-2 text-sm text-zinc-500">选择一个工具，快速处理语言学习中的常见任务。</p>
        </header>

        <section className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
          {TOOLS.map(({ id, name, description, icon: Icon, path }) => (
            <Link key={id} to={path} className="group flex min-h-52 flex-col rounded-xl border border-zinc-800 bg-zinc-950/60 p-5 transition-all hover:-translate-y-0.5 hover:border-teal-800 hover:bg-zinc-950 hover:shadow-lg hover:shadow-black/20">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-teal-900 bg-teal-950/50 text-teal-300"><Icon size={20} /></div>
              <h2 className="mt-5 font-medium text-zinc-100">{name}</h2>
              <p className="mt-2 flex-1 text-sm leading-6 text-zinc-500">{description}</p>
              <span className="mt-5 flex items-center gap-1 text-xs text-zinc-500 transition-colors group-hover:text-teal-300">打开工具<ArrowRight size={14} className="transition-transform group-hover:translate-x-1" /></span>
            </Link>
          ))}
        </section>
      </div>
    </div>
  )
}
