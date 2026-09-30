import { useState } from 'react'

/**
 * 分类树节点的折叠状态。
 *
 * 取值优先级：用户手动操作 > 选中路径 > 默认折叠。
 *
 * 雅思树有三层，默认全展开会占满侧边栏/下拉面板；但选中项所在的祖先链必须
 * 自动展开，否则用户点了某分类却看不到它在哪里。
 *
 * 用派生而不是 useEffect 同步状态：选中目标一变，`manual` 因 anchor 不匹配
 * 自动失效，重新跟随选中路径。这样既免了一次多余渲染，也没有"先渲染折叠、
 * effect 再展开"的闪烁。
 */
export function useTreeNodeOpen(
  selectedId: string | undefined,
  isOnActivePath: boolean,
) {
  const [manual, setManual] = useState<{ at: string; value: boolean } | null>(null)
  const anchor = selectedId ?? ''
  const open = (manual?.at === anchor ? manual.value : null) ?? isOnActivePath
  const toggle = () => setManual({ at: anchor, value: !open })
  return { open, toggle }
}

/** 从分类树里找出到目标分类的祖先链（含自身），用于自动展开。 */
export function collectActivePath(
  tree: { id: string; children?: { id: string; children?: unknown[] }[] }[],
  targetId: string | undefined,
): Set<string> {
  const ids = new Set<string>()
  if (!targetId) return ids

  const walk = (
    nodes: { id: string; children?: { id: string; children?: unknown[] }[] }[],
    trail: string[],
  ): boolean => {
    for (const node of nodes) {
      const next = [...trail, node.id]
      if (node.id === targetId) {
        next.forEach((id) => ids.add(id))
        return true
      }
      if (node.children?.length && walk(node.children as never, next)) return true
    }
    return false
  }

  walk(tree, [])
  return ids
}
