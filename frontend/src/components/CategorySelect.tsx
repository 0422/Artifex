import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

import type { KnowledgeCategory } from '../lib/types'
// 2026-09-30 折叠逻辑与侧边栏共用一套，避免两份实现行为漂移
import { collectActivePath, useTreeNodeOpen } from '../lib/useTreeNodeOpen'

/**
 * 分类树下拉。原生 <select> 表达不了树，所以做成自定义面板：
 * 默认只显示根层，点 chevron 逐级展开，选中路径自动展开。
 *
 * 响应式由调用方决定——这里不写 lg:hidden，否则放进弹窗里桌面端会被隐藏。
 */
export default function CategorySelect({
  categories,
  selected,
  onSelect,
  rootLabel = '全部场景',
  className = '',
}: {
  categories: KnowledgeCategory[]
  selected: KnowledgeCategory | null
  onSelect: (category: KnowledgeCategory | null) => void
  rootLabel?: string
  className?: string
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  // 点击面板外关闭
  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown, true)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown, true)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const activePath = useMemo(
    () => collectActivePath(categories, selected?.id),
    [categories, selected?.id],
  )

  const pick = (category: KnowledgeCategory | null) => {
    onSelect(category)
    setOpen(false)
  }

  return (
    <div ref={rootRef} className={`relative w-full ${className}`}>
      <button
        type="button"
        aria-haspopup="tree"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="field flex h-9 w-full items-center justify-between gap-2 py-1 text-left"
      >
        <span className="truncate">{selected?.name ?? '全部场景'}</span>
        <ChevronDown size={15} className={`shrink-0 text-zinc-500 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          role="tree"
          className="absolute inset-x-0 top-full z-50 mt-1 max-h-80 overflow-y-auto rounded-md border border-zinc-700 bg-zinc-950 p-1.5 shadow-2xl"
        >
          <button
            onClick={() => pick(null)}
            className={`flex w-full items-center rounded px-2.5 py-1.5 text-left text-sm ${selected === null ? 'bg-teal-950 text-teal-300' : 'text-zinc-400 hover:bg-zinc-900'}`}
          >
            {rootLabel}
          </button>
          {categories.map((node) => (
            <TreeNode
              key={node.id}
              node={node}
              depth={0}
              selectedId={selected?.id}
              activePath={activePath}
              onSelect={pick}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function TreeNode({
  node,
  depth,
  selectedId,
  activePath,
  onSelect,
}: {
  node: KnowledgeCategory
  depth: number
  selectedId?: string
  activePath: Set<string>
  onSelect: (category: KnowledgeCategory) => void
}) {
  const { open, toggle } = useTreeNodeOpen(selectedId, activePath.has(node.id))
  const isSelected = selectedId === node.id

  return (
    <div>
      <div
        className={`group flex items-center rounded transition-colors ${isSelected ? 'bg-teal-950 text-teal-300' : 'text-zinc-400 hover:bg-zinc-900'}`}
      >
        <button
          type="button"
          title={open ? '收起' : '展开'}
          onClick={toggle}
          className={`grid h-7 w-7 shrink-0 place-items-center rounded text-zinc-500 hover:text-zinc-200 ${node.children.length ? '' : 'invisible'}`}
        >
          {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </button>
        <button
          type="button"
          onClick={() => onSelect(node)}
          className="flex min-w-0 flex-1 items-center justify-between gap-2 py-1.5 pr-2 text-left text-sm"
        >
          <span className="truncate">{node.name}</span>
          {node.card_count > 0 && (
            <span className="shrink-0 text-[10px] tabular-nums text-zinc-600">{node.card_count}</span>
          )}
        </button>
      </div>
      {open && node.children.length > 0 && (
        <div className="ml-3.5 border-l border-zinc-800/80 pl-1.5">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              activePath={activePath}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}
