import { Boxes } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface ToolDefinition {
  id: string
  name: string
  description: string
  icon: LucideIcon
  path: string
}

// 2026-10-01 学习路径、内容捕获、文本统计、英文大小写转换、逐行去重五个工具卡片已下线，
// 相关页面（ToolPage/PathPage/CapturePage）与轻量组件一并删除。
// 仅保留集装箱装载计算器：它有自己的完整页面和独立路由，不走这里的 component 渲染。
export const TOOLS: ToolDefinition[] = [
  {
    id: 'container-loading-calculator',
    name: '集装箱装载计算器',
    description: '配置集装箱和货物 SKU，计算空间与载重利用率，并查看可交互的三维装载方案。',
    icon: Boxes,
    path: '/tools/container-loading-calculator',
  },
]
