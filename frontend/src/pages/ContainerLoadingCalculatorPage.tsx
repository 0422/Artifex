import { ArrowLeft, Boxes } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function ContainerLoadingCalculatorPage() {
  const [loading, setLoading] = useState(true)

  return (
    <div className="flex h-full min-h-[720px] flex-col bg-zinc-900">
      <header className="shrink-0 border-b border-zinc-800 bg-zinc-950/70 px-8 py-3 lg:px-10">
        <div className="flex items-center gap-4">
          <Link to="/tools" title="返回工具库" aria-label="返回工具库" className="icon-button"><ArrowLeft size={19} /></Link>
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-teal-900 bg-teal-950/50 text-teal-300"><Boxes size={20} /></div>
          <div><h1 className="font-semibold text-zinc-100">集装箱装载计算器</h1><p className="mt-0.5 text-xs text-zinc-500">配置集装箱和货物 SKU，计算并查看三维装载方案</p></div>
        </div>
      </header>
      <div className="relative min-h-0 flex-1 bg-[#1a1d2e]">
        {loading && <div className="absolute inset-0 z-10 grid place-items-center bg-[#1a1d2e] text-sm text-zinc-400">正在加载三维计算器...</div>}
        <iframe
          src="/tools/container-loading-calculator.html"
          title="集装箱装载计算器"
          className="h-full min-h-[650px] w-full border-0"
          sandbox="allow-scripts allow-same-origin allow-downloads allow-forms"
          onLoad={() => setLoading(false)}
        />
      </div>
    </div>
  )
}
