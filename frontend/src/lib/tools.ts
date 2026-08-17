import { ALargeSmall, Boxes, ListFilter, Route, ScanText, TextCursorInput } from 'lucide-react'
import type { ComponentType } from 'react'
import type { LucideIcon } from 'lucide-react'

import CaseConverterTool from '../components/tools/CaseConverterTool'
import LineDeduplicatorTool from '../components/tools/LineDeduplicatorTool'
import TextStatisticsTool from '../components/tools/TextStatisticsTool'

export interface ToolDefinition {
  id: string
  name: string
  description: string
  icon: LucideIcon
  path: string
  component?: ComponentType
}

export const TOOLS: ToolDefinition[] = [
  {
    id: 'container-loading-calculator',
    name: '集装箱装载计算器',
    description: '配置集装箱和货物 SKU，计算空间与载重利用率，并查看可交互的三维装载方案。',
    icon: Boxes,
    path: '/tools/container-loading-calculator',
  },
  {
    id: 'learning-path',
    name: '学习路径',
    description: '查看根据引导结果生成的阶段目标、能力起点和个性化学习建议。',
    icon: Route,
    path: '/tools/learning-path',
  },
  {
    id: 'content-capture',
    name: '内容捕获',
    description: '粘贴学习材料，由 AI 提取关键概念、生成摘要和记忆卡片。',
    icon: ScanText,
    path: '/tools/content-capture',
  },
  {
    id: 'text-statistics',
    name: '文本统计',
    description: '快速统计文本的字符数、单词数和行数，辅助评估阅读与写作篇幅。',
    icon: TextCursorInput,
    path: '/tools/text-statistics',
    component: TextStatisticsTool,
  },
  {
    id: 'case-converter',
    name: '英文大小写转换',
    description: '在大写、小写、标题格式和句首大写之间快速转换英文文本。',
    icon: ALargeSmall,
    path: '/tools/case-converter',
    component: CaseConverterTool,
  },
  {
    id: 'line-deduplicator',
    name: '逐行去重',
    description: '删除词汇表或句子列表中的重复行，并保留原有排列顺序。',
    icon: ListFilter,
    path: '/tools/line-deduplicator',
    component: LineDeduplicatorTool,
  },
]

export const findTool = (id: string | undefined) => TOOLS.find((tool) => tool.id === id)
