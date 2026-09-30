import { useEffect, useMemo, useState } from 'react'
import { BookOpen, ChevronDown, ChevronRight, Library, MessageSquareText, Pencil, Plus, Search, Trash2, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import type { KnowledgeCategory, Scenario, ScenarioInput, ScenarioLanguage, ScenarioMode } from '../lib/types'
// 2026-09-30 雅思口语场景库：Part 徽章名与根分类名
import { IELTS_PART_LABEL, IELTS_ROOT_CATEGORY } from '../lib/constants'
// 2026-09-30 删除/重命名入口配套的确认弹窗
import ConfirmDialog from '../components/ConfirmDialog'
// 2026-09-30 分类树右键菜单（重命名 / 删除）
import CategoryContextMenu from '../components/CategoryContextMenu'
// 2026-09-30 折叠状态与「选中路径自动展开」的共用逻辑
import { collectActivePath, useTreeNodeOpen } from '../lib/useTreeNodeOpen'
// 2026-09-30 官方题库只读提示
import InfoDialog from '../components/InfoDialog'
// 2026-09-30 小屏可折叠分类树下拉，替代原生 <select>
import CategorySelect from '../components/CategorySelect'
import { knowledgeApi, scenarioApi } from '../services/api'

const DOMAIN_LABEL: Record<string, string> = {
  language: '语言', history: '历史', politics: '政治', art: '艺术', film: '电影', custom: '自定义',
}
const MODE_LABEL: Record<ScenarioMode, string> = {
  role_play: '角色扮演', guided_discussion: '主题讨论', socratic_dialogue: '苏格拉底问答', debate: '观点辩论', source_analysis: '资料分析', work_analysis: '作品赏析',
}
const LANGUAGE_LABEL: Record<ScenarioLanguage, string> = { en: '英语', ja: '日语', zh: '中文' }

const emptyScenario = (domain = 'language', categoryId?: string): ScenarioInput => ({
  title: '',
  description: '',
  domain,
  language: domain === 'language' ? 'ja' : 'zh',
  difficulty: domain === 'language' ? 'N3' : 'intermediate',
  scenario_mode: domain === 'language' ? 'role_play' : 'guided_discussion',
  estimated_minutes: 15,
  tags: [],
  category_ids: categoryId ? [categoryId] : [],
  // 2026-09-30 雅思口语场景库：默认非雅思，选中雅思分类时由 openEditor 覆盖
  ielts_part: null,
  cue_card: null,
})

// 2026-09-30 雅思口语场景库：从根到目标分类的路径上找 "雅思口语" 与 "Part N"。
// 用户常在叶子类别（如「个人喜好类」）下新建，路径判定才能反推出属于哪个 part。
function findCategoryPath(tree: KnowledgeCategory[], id: string | undefined): KnowledgeCategory[] | null {
  if (!id) return null
  for (const node of tree) {
    if (node.id === id) return [node]
    const found = findCategoryPath(node.children, id)
    if (found) return [node, ...found]
  }
  return null
}

function detectIeltsPart(tree: KnowledgeCategory[], category: KnowledgeCategory | null): number | null {
  if (!category) return null
  const path = findCategoryPath(tree, category.id)
  if (!path || !path.some((node) => node.name === IELTS_ROOT_CATEGORY)) return null
  for (const node of path) {
    const matched = /^Part\s*([123])$/.exec(node.name)
    if (matched) return Number(matched[1])
  }
  return null
}

// 2026-09-30 把后端返回的 detail 透出来。此前 catch 里只写"场景保存失败"，
// 结果 500 的真实原因被吞掉，只能看到一句无从排查的提示。
// 放在组件外：它不依赖任何 state，也避免在 useEffect 之前被引用。
function describeSaveError(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: unknown } })?.response?.data
  const detail = (data as { detail?: unknown })?.detail
  if (typeof detail === 'string' && detail) return detail
  // Pydantic 422 的 errors 数组里带字段级原因
  const errors = (data as { errors?: Array<{ loc?: unknown[]; msg?: string }> })?.errors
  if (Array.isArray(errors) && errors.length) {
    const first = errors[0]
    const field = Array.isArray(first?.loc) ? first.loc[first.loc.length - 1] : undefined
    return `${field ? `${field}: ` : ''}${first?.msg ?? '输入不合法'}`
  }
  return (err as { message?: string })?.message || fallback
}

export default function KnowledgePage() {
  const navigate = useNavigate()
  const [categories, setCategories] = useState<KnowledgeCategory[]>([])
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [selectedCategory, setSelectedCategory] = useState<KnowledgeCategory | null>(null)
  const [selected, setSelected] = useState<Scenario | null>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editor, setEditor] = useState<Scenario | 'new' | null>(null)
  const [form, setForm] = useState<ScenarioInput>(() => emptyScenario())
  const [categoryEditorOpen, setCategoryEditorOpen] = useState(false)
  // 2026-09-30 右键菜单位置与目标分类；为 null 表示菜单关闭
  const [menu, setMenu] = useState<{ x: number; y: number; target: KnowledgeCategory } | null>(null)
  // 2026-09-30 官方题库只读的提示弹窗（右键菜单点了 rename/delete 时给反馈）
  const [info, setInfo] = useState<{ title: string; message: string } | null>(null)

  const loadCategories = () => knowledgeApi.categoryTree().then(setCategories)
  const loadScenarios = (category = selectedCategory, search = query) => {
    setLoading(true)
    return scenarioApi.list(false, {
      category_id: category?.id,
      q: search.trim() || undefined,
    }).then((data) => {
      setScenarios(data)
      setSelected((current) => data.find((item) => item.id === current?.id) ?? data[0] ?? null)
    }).catch(() => setError('知识库内容加载失败')).finally(() => setLoading(false))
  }

  useEffect(() => {
    Promise.all([loadCategories(), scenarioApi.list()]).then(([, data]) => {
      setScenarios(data)
      setSelected(data[0] ?? null)
    }).catch((err) => setError(describeSaveError(err, '知识库加载失败'))).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => { void loadScenarios(selectedCategory, query) }, 250)
    return () => window.clearTimeout(timer)
  }, [query, selectedCategory]) // eslint-disable-line react-hooks/exhaustive-deps

  // 2026-10-01 扁平分类列表已不再使用：新建场景/新建分类的 select 都换成了可折叠树。
  // const categoryOptions = useMemo(() => flattenCategories(categories), [categories])

  // 2026-09-30 选中分类的祖先链（含自身）。树默认折叠，靠这个自动展开选中路径
  const activePath = useMemo(
    () => collectActivePath(categories, selectedCategory?.id),
    [categories, selectedCategory?.id],
  )

  const openEditor = (scenario?: Scenario) => {
    setError('')
    setEditor(scenario ?? 'new')
    if (scenario) {
      setForm({
        title: scenario.title,
        description: scenario.description,
        language: scenario.language,
        difficulty: scenario.difficulty,
        domain: scenario.domain,
        scenario_mode: scenario.scenario_mode,
        estimated_minutes: scenario.estimated_minutes,
        tags: scenario.tags,
        category_ids: scenario.categories.map((category) => category.id),
        ielts_part: scenario.ielts_part,
        cue_card: scenario.cue_card,
      })
      return
    }
    // 2026-09-30 雅思口语场景库：按选中类别自动判定 part，并换一套默认值
    // （雅思用英语 + CEFR 难度，而不是沿用日语场景的 ja/N3）
    const part = detectIeltsPart(categories, selectedCategory)
    const base = emptyScenario(selectedCategory?.domain, selectedCategory?.id)
    // 2026-09-30 难度不再由用户选：这里只留 language，difficulty 交给后端按语言推默认值
    setForm(
      part
        ? {
            ...base,
            language: 'en',
            scenario_mode: 'guided_discussion',
            ielts_part: part,
            tags: ['ielts', `part${part}`],
          }
        : base,
    )
  }

  // 2026-09-30 把后端返回的 detail 透出来。此前 catch 里只写"场景保存失败"，
  // 结果 500 的真实原因被吞掉，只能看到一句无从排查的提示。
  const saveScenario = async () => {
    if (!form.title.trim() || !form.description.trim()) return
    try {
      const saved = editor === 'new'
        ? await scenarioApi.create(form)
        : await scenarioApi.update((editor as Scenario).id, form)
      setEditor(null)
      await Promise.all([loadCategories(), loadScenarios()])
      setSelected(saved)
    } catch (err) {
      setError(describeSaveError(err, '场景保存失败，请检查输入内容'))
    }
  }

  // 2026-09-30 新增删除能力：后端 DELETE /scenarios/{id} 与 /knowledge/categories/{id}
  // 一早就有，但前端始终没给入口，导致自建的类别/场景删不掉。
  // 官方共享内容后端会返 403，这里把 detail 翻成中文提示。
  const [categoryEditing, setCategoryEditing] = useState<KnowledgeCategory | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [confirm, setConfirm] = useState<
    { kind: 'scenario'; target: Scenario } | { kind: 'category'; target: KnowledgeCategory } | null
  >(null)

  const describeDeleteError = (err: unknown, fallback: string) => {
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    if (typeof detail === 'string' && detail) {
      return detail.includes('只读') ? '官方题库为只读，不可删除' : detail
    }
    return (err as { message?: string })?.message || fallback
  }

  const runDelete = async () => {
    if (!confirm) return
    setDeleting(true)
    setError('')
    try {
      if (confirm.kind === 'scenario') {
        await scenarioApi.remove(confirm.target.id)
        setSelected(null)
      } else {
        await knowledgeApi.archiveCategory(confirm.target.id)
        // 删掉的正是当前选中的分类时退回"全部场景"，否则列表还停在已删除的分类上
        if (selectedCategory?.id === confirm.target.id) setSelectedCategory(null)
      }
      await Promise.all([loadCategories(), loadScenarios()])
      setConfirm(null)
    } catch (err) {
      setError(describeDeleteError(err, '删除失败，请稍后重试'))
      setConfirm(null)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 bg-zinc-900">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950 lg:flex">
        <div className="flex h-14 items-center justify-between border-b border-zinc-800 px-4">
          <div><h1 className="text-sm font-semibold text-zinc-100">知识分类</h1><p className="text-xs text-zinc-500">右键分类可重命名或删除</p></div>
          <button title="新建分类" aria-label="新建分类" onClick={() => setCategoryEditorOpen(true)} className="icon-button"><Plus size={16} /></button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          <button onClick={() => setSelectedCategory(null)} className={`flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm ${selectedCategory === null ? 'bg-teal-950 text-teal-300' : 'text-zinc-400 hover:bg-zinc-900'}`}><Library size={16} />全部场景</button>
          <div className="mt-2 space-y-0.5">{categories.map((category) => <CategoryNode key={category.id} category={category} selectedId={selectedCategory?.id} activePath={activePath} onSelect={setSelectedCategory} onContextMenu={(node, event) => { event.preventDefault(); setMenu({ x: event.clientX, y: event.clientY, target: node }) }} />)}</div>        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-14 shrink-0 flex-wrap items-center gap-3 border-b border-zinc-800 px-4 py-2 sm:px-6">
          <div className="min-w-0 flex-1"><h1 className="truncate text-sm font-semibold text-zinc-100">{selectedCategory?.name ?? '全部场景'}</h1><p className="text-xs text-zinc-500">{loading ? '正在加载...' : `${scenarios.length} 张学习场景卡`}</p></div>
          {/* 2026-09-30 原生 select 表达不了树，改为可折叠树下拉（与侧边栏同一套折叠逻辑）。
              仅小屏显示：lg:hidden 由调用方控制，组件本身不写死 */}
          <div className="lg:hidden"><CategorySelect categories={categories} selected={selectedCategory} onSelect={setSelectedCategory} /></div>
          <label className="flex h-9 min-w-44 flex-1 items-center gap-2 rounded border border-zinc-700 bg-zinc-950 px-3 sm:max-w-xs"><Search size={15} className="text-zinc-500" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题或说明" className="min-w-0 flex-1 bg-transparent text-sm text-zinc-200 outline-none" /></label>
          <button onClick={() => openEditor()} className="primary-button"><Plus size={15} />新建场景</button>
        </header>
        {error && <p className="border-b border-red-900 bg-red-950/40 px-5 py-2 text-xs text-red-300">{error}</p>}
        <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
          {!loading && scenarios.length === 0 && <EmptyState onCreate={() => openEditor()} />}
          <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">{scenarios.map((scenario) => <ScenarioCard key={scenario.id} scenario={scenario} selected={selected?.id === scenario.id} onClick={() => setSelected(scenario)} />)}</div>
        </div>
      </section>

      <aside className={`${selected ? 'flex' : 'hidden'} fixed inset-y-0 right-0 z-40 w-full max-w-md flex-col border-l border-zinc-700 bg-zinc-950 shadow-2xl xl:static xl:z-auto xl:w-96 xl:shadow-none`}>
        {selected && <ScenarioPreview scenario={selected} onClose={() => setSelected(null)} onEdit={() => openEditor(selected)} onStart={() => navigate(`/chat?scenario=${selected.id}`)} onDelete={() => setConfirm({ kind: 'scenario', target: selected })} />}
      </aside>

      {editor && <ScenarioEditor form={form} tree={categories} editing={editor !== 'new'} onChange={setForm} onClose={() => setEditor(null)} onSave={saveScenario} />}
      {categoryEditorOpen && <CategoryEditor tree={categories} editing={categoryEditing} onClose={() => { setCategoryEditorOpen(false); setCategoryEditing(null) }} onSaved={async () => { setCategoryEditorOpen(false); setCategoryEditing(null); await Promise.all([loadCategories(), loadScenarios()]) }} />}
      {menu && (
        <CategoryContextMenu
          x={menu.x}
          y={menu.y}
          name={menu.target.name}
          onAction={(action) => {
            const target = menu.target
            setMenu(null)
            if (action === 'rename') {
              if (target.is_shared) {
                setInfo({ title: '官方题库不可修改', message: `「${target.name}」属于官方共享题库，对所有用户只读。\n你可以在它下面新建自己的子分类或场景。` })
                return
              }
              setCategoryEditing(target)
              setCategoryEditorOpen(true)
              return
            }
            // 删除：官方共享的也给反馈，而不是静默无响应
            if (target.is_shared) {
              setInfo({ title: '官方题库不可删除', message: `「${target.name}」属于官方共享题库，对所有用户只读。\n删除它会影响所有人，所以这里不允许删除。` })
              return
            }
            setConfirm({ kind: 'category', target })
          }}
          onClose={() => setMenu(null)}
        />
      )}
      {info && <InfoDialog title={info.title} message={info.message} onClose={() => setInfo(null)} />}
      {confirm && (
        <ConfirmDialog
          title={confirm.kind === 'scenario' ? '删除场景卡' : '删除分类'}
          message={
            confirm.kind === 'scenario'
              ? `确定删除「${confirm.target.title}」吗？该场景的历史对话记录不受影响。`
              : `确定删除「${confirm.target.name}」吗？其下的子分类会一并删除。`
          }
          busy={deleting}
          onConfirm={runDelete}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  )
}

// 2026-09-30 改为默认折叠的树：雅思树有三层，全部展开会占满侧边栏。
// 但选中项所在的祖先链必须自动展开，否则用户点了某分类却看不到它在哪。
function CategoryNode({ category, selectedId, activePath, onSelect, onContextMenu }: { category: KnowledgeCategory; selectedId?: string; activePath?: Set<string>; onSelect: (category: KnowledgeCategory) => void; onContextMenu: (category: KnowledgeCategory, event: React.MouseEvent) => void }) {
  // open 的取值优先级：用户手动操作 > 选中路径 > 默认折叠。
  // 用派生而非 useEffect 同步状态，避免多余渲染与初始闪烁。
  // 折叠逻辑与 CategorySelect 共用 useTreeNodeOpen，防止两份实现行为漂移。
  const { open, toggle } = useTreeNodeOpen(selectedId, activePath?.has(category.id) ?? false)
  return <div><div onContextMenu={(event) => onContextMenu(category, event)} className={`group flex items-center rounded transition-colors ${selectedId === category.id ? 'bg-teal-950 text-teal-300' : 'text-zinc-400 hover:bg-zinc-900'} cursor-context-menu`}>
    <button title={open ? '收起分类' : '展开分类'} onClick={toggle} className={`grid h-7 w-7 shrink-0 place-items-center rounded text-zinc-500 transition-colors hover:text-zinc-200 ${category.children.length ? '' : 'invisible'}`}>{open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}</button>
    <button onClick={() => onSelect(category)} className="flex min-w-0 flex-1 items-center justify-between gap-2 py-1.5 pr-2 text-left text-sm"><span className="truncate">{category.name}</span>{category.card_count > 0 && <span className="shrink-0 text-[10px] tabular-nums text-zinc-600">{category.card_count}</span>}</button>
  </div>{open && category.children.length > 0 && <div className="ml-3.5 border-l border-zinc-800/80 pl-1.5">{category.children.map((child) => <CategoryNode key={child.id} category={child} selectedId={selectedId} activePath={activePath} onSelect={onSelect} onContextMenu={onContextMenu} />)}</div>}</div>
}

function ScenarioCard({ scenario, selected, onClick }: { scenario: Scenario; selected: boolean; onClick: () => void }) {
  return <button onClick={onClick} className={`min-h-44 rounded-lg border p-4 text-left transition-colors ${selected ? 'border-teal-700 bg-teal-950/30' : 'border-zinc-800 bg-zinc-950/50 hover:border-zinc-700 hover:bg-zinc-900'}`}>
    <div className="flex items-start justify-between gap-3">
      {/* 2026-09-30 雅思场景优先显示 Part 徽章，非雅思仍显示领域 */}
      {scenario.ielts_part ? (
        <span className="rounded bg-teal-950 px-2 py-1 text-[10px] text-teal-300">雅思 {IELTS_PART_LABEL[scenario.ielts_part]}</span>
      ) : (
        <span className="rounded bg-zinc-800 px-2 py-1 text-[10px] text-zinc-400">{DOMAIN_LABEL[scenario.domain] ?? scenario.domain}</span>
      )}
      <span className="text-[10px] text-zinc-600">{MODE_LABEL[scenario.scenario_mode]}</span>
    </div>
    <h2 className="mt-4 font-medium text-zinc-100">{scenario.title}</h2><p className="mt-2 line-clamp-3 text-xs leading-5 text-zinc-500">{scenario.description}</p>
    <div className="mt-4 flex flex-wrap items-center gap-2 text-[10px] text-zinc-500"><span>{LANGUAGE_LABEL[scenario.language]}</span>{scenario.estimated_minutes && <><span>·</span><span>{scenario.estimated_minutes} 分钟</span></>}</div>
  </button>
}

function ScenarioPreview({ scenario, onClose, onEdit, onStart, onDelete }: { scenario: Scenario; onClose: () => void; onEdit: () => void; onStart: () => void; onDelete: () => void }) {
  // 2026-09-30 雅思口语场景库：Part 徽章 + Part 2 题卡醒目展示
  const part = scenario.ielts_part
  // 官方共享场景后端会返 403，这里直接不给按钮
  const isShared = scenario.is_shared
  return <><header className="flex h-14 items-center justify-between border-b border-zinc-800 px-4"><span className="text-sm font-semibold">场景预览</span><button onClick={onClose} title="关闭预览" className="icon-button"><X size={17} /></button></header>
    <div className="min-h-0 flex-1 overflow-y-auto p-6"><div className="flex flex-wrap gap-2">{part ? <span className="rounded bg-teal-950 px-2 py-1 text-xs text-teal-300">雅思 {IELTS_PART_LABEL[part]}</span> : null}<span className="rounded bg-zinc-900 px-2 py-1 text-xs text-zinc-400">{MODE_LABEL[scenario.scenario_mode]}</span>{!part && <span className="rounded bg-teal-950 px-2 py-1 text-xs text-teal-300">{DOMAIN_LABEL[scenario.domain] ?? scenario.domain}</span>}</div><h2 className="mt-5 text-xl font-semibold text-zinc-100">{scenario.title}</h2>
      {part === 2 && scenario.cue_card && (
        <div className="mt-5 rounded-lg border border-teal-900/70 bg-teal-950/25 p-4">
          <h3 className="text-xs font-medium text-teal-300">Cue card 题卡</h3>
          <p className="mt-2 whitespace-pre-wrap font-mono text-sm leading-6 text-zinc-200">{scenario.cue_card}</p>
        </div>
      )}
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-zinc-400">{scenario.description}</p>
      {/* 2026-09-30 去掉难度/预计时长：新建已不收集，预览里留着只有空值和噪音 */}
      <dl className="mt-6 divide-y divide-zinc-800 border-y border-zinc-800 text-sm"><Info label="输出语言" value={LANGUAGE_LABEL[scenario.language]} /><Info label="分类" value={scenario.categories.map((item) => item.name).join(' / ') || '未分类'} /></dl>
      {scenario.tags.length > 0 && <div className="mt-6"><h3 className="text-xs text-zinc-500">主题标签</h3><div className="mt-2 flex flex-wrap gap-2">{scenario.tags.map((tag) => <span key={tag} className="rounded-full border border-zinc-700 px-2 py-1 text-xs text-zinc-400">{tag}</span>)}</div></div>}
    </div><footer className="flex gap-2 border-t border-zinc-800 p-4"><button onClick={onEdit} className="secondary-button"><Pencil size={15} />编辑</button>{!isShared && <button onClick={onDelete} title="删除场景" className="secondary-button text-red-300 hover:border-red-800"><Trash2 size={15} />删除</button>}<button onClick={onStart} className="primary-button flex-1"><MessageSquareText size={15} />开始对话</button></footer></>
}

function Info({ label, value }: { label: string; value: string }) { return <div className="flex justify-between gap-4 py-3"><dt className="text-zinc-500">{label}</dt><dd className="text-right text-zinc-300">{value}</dd></div> }

function EmptyState({ onCreate }: { onCreate: () => void }) { return <div className="mx-auto max-w-sm py-24 text-center"><BookOpen className="mx-auto text-zinc-700" size={34} /><h2 className="mt-4 font-medium text-zinc-300">这里还没有学习场景</h2><p className="mt-2 text-sm text-zinc-600">创建第一张场景卡，或切换到其他分类浏览。</p><button onClick={onCreate} className="primary-button mt-5"><Plus size={15} />新建场景</button></div> }

// 2026-09-30 雅思分类下场景类型只保留「主题讨论」：雅思对话由 ielts_part 接管
// （考官追问 / 题卡独白 / 抽象追问），scenario_mode 实际不参与，列出其余选项只会误导。
const MODE_LABEL_IELTS: Record<string, string> = { guided_discussion: '主题讨论' }

function ScenarioEditor({ form, tree, editing, onChange, onClose, onSave }: { form: ScenarioInput; tree: KnowledgeCategory[]; editing: boolean; onChange: (form: ScenarioInput) => void; onClose: () => void; onSave: () => void }) {
  const language = form.language
  // 已由左侧选中的分类决定领域/分类时，不再重复让用户选
  const categoryLocked = Boolean(form.category_ids?.length)
  // 分类落在雅思树下时，Part 是确定的，不给"非雅思场景"这个会造成歧义的选项
  const isIelts = form.ielts_part != null
  const modeOptions = isIelts ? MODE_LABEL_IELTS : MODE_LABEL
  return <div className="fixed inset-0 z-50 flex justify-end bg-black/70"><div className="flex h-full w-full max-w-xl flex-col border-l border-zinc-700 bg-zinc-900 shadow-2xl"><header className="flex h-14 items-center justify-between border-b border-zinc-800 px-5"><h2 className="font-semibold">{editing ? '编辑学习场景' : '新建学习场景'}</h2><button onClick={onClose} className="icon-button"><X size={17} /></button></header><div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
    <Field label="场景名称"><input autoFocus className="field mt-1.5" value={form.title} onChange={(event) => onChange({ ...form, title: event.target.value })} placeholder="例如：讨论王安石变法" /></Field>
    <Field label="场景说明"><textarea className="field mt-1.5 min-h-28 resize-y" value={form.description} onChange={(event) => onChange({ ...form, description: event.target.value })} placeholder="说明学习目标、讨论背景和 AI 应如何参与" /></Field>
    {/* 2026-09-30 分类已由左侧确定时隐藏，避免重复询问造成歧义 */}
    {!categoryLocked && (
      <>
        <div className="grid grid-cols-2 gap-3"><Field label="领域"><select className="field mt-1.5" value={form.domain} onChange={(event) => { const domain = event.target.value; onChange({ ...emptyScenario(domain), title: form.title, description: form.description }) }}>{Object.entries(DOMAIN_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field></div>
        <Field label="分类">
          {/* 2026-09-30 改用可折叠树：原生 select 只能摊平显示路径，四层树下拉里很难找 */}
          <CategorySelect
            categories={tree.filter((node) => node.domain === form.domain)}
            selected={findCategoryPath(tree, form.category_ids?.[0])?.at(-1) ?? null}
            rootLabel="未分类"
            onSelect={(node) => {
              onChange({ ...form, category_ids: node ? [node.id] : [] })
              // 换了分类要重判雅思 Part：Part 由分类路径决定，不能让上一处残留
              const part = detectIeltsPart(tree, node)
              if (part !== form.ielts_part) {
                onChange({
                  ...form,
                  category_ids: node ? [node.id] : [],
                  ielts_part: part,
                  cue_card: part === 2 ? form.cue_card : null,
                })
              }
            }}
          />
        </Field>
      </>
    )}
    {categoryLocked && (
      <p className="rounded border border-zinc-800 bg-zinc-950/40 px-3 py-2 text-xs text-zinc-500">
        所属分类：
        <span className="text-zinc-300">
          {findCategoryPath(tree, form.category_ids?.[0])?.map((node) => node.name).join(' › ') || '未分类'}
        </span>
      </p>
    )}
    {/* 2026-09-30 难度与预计时长都不再收集：难度由后端按输出语言取默认值 */}
    <Field label="场景类型"><select className="field mt-1.5" value={form.scenario_mode} onChange={(event) => onChange({ ...form, scenario_mode: event.target.value as ScenarioMode })}>{Object.entries(modeOptions).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
    <Field label="输出语言"><select className="field mt-1.5" value={language} onChange={(event) => onChange({ ...form, language: event.target.value as ScenarioLanguage })}>{Object.entries(LANGUAGE_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field>
    {/* 2026-09-30 雅思口语场景库：Part 选择 + Part 2 专属题卡 */}
    <div className="rounded border border-zinc-800 bg-zinc-950/40 p-3">
      <Field label="雅思 Part">
        <select className="field mt-1.5" value={form.ielts_part ?? ''} onChange={(event) => onChange({ ...form, ielts_part: event.target.value ? Number(event.target.value) : null, cue_card: event.target.value === '2' ? form.cue_card : null })}>
          {/* 已在雅思分类下时不给"非雅思场景"，否则用户会以为选错地方 */}
          {!isIelts && <option value="">非雅思场景</option>}
          {[1, 2, 3].map((part) => <option key={part} value={part}>{IELTS_PART_LABEL[part]}</option>)}
        </select>
      </Field>
      <p className="mt-1.5 text-[11px] leading-5 text-zinc-600">
        选定后对话会切换为雅思考官模式：Part 1 逐题追问，Part 2 出示题卡请你独白，Part 3 抽象追问。
      </p>
      {form.ielts_part === 2 && (
        <Field label="Cue card 题卡">
          <textarea className="field mt-1.5 min-h-28 resize-y font-mono text-xs leading-6" value={form.cue_card ?? ''} onChange={(event) => onChange({ ...form, cue_card: event.target.value })} placeholder={'You should say:\nwho this person is\nand explain why you admire this person.'} />
        </Field>
      )}
      {form.ielts_part === 1 || form.ielts_part === 3 ? (
        <p className="mt-2 text-[11px] leading-5 text-zinc-600">
          题库题目请按<b className="text-zinc-500">一行一题</b>填写在「场景说明」里：对话只会先问第一题，其余由考官按需追问。
        </p>
      ) : null}
    </div>
    <Field label="标签（使用逗号分隔）"><input className="field mt-1.5" value={(form.tags ?? []).join(', ')} onChange={(event) => onChange({ ...form, tags: event.target.value.split(/[,，]/).map((tag) => tag.trim()).filter(Boolean) })} placeholder="政策, 财政, 宋代" /></Field>
  </div><footer className="flex justify-end gap-2 border-t border-zinc-800 p-4"><button onClick={onClose} className="secondary-button">取消</button><button disabled={!form.title.trim() || !form.description.trim()} onClick={onSave} className="primary-button">保存场景</button></footer></div></div>
}

function CategoryEditor({ tree, editing, onClose, onSaved }: { tree: KnowledgeCategory[]; editing?: KnowledgeCategory | null; onClose: () => void; onSaved: () => void }) {
  // 2026-09-30 补上编辑模式：此前只有新建，导致建错的分类没法改名，只能留着或让后端删。
  // editing 非空即重命名模式，此时锁定父分类（移动分类会牵动整棵子树，暂不支持）。
  const isRenaming = Boolean(editing)
  const [name, setName] = useState(editing?.name ?? '')
  // 2026-09-30 去掉「所属领域」下拉：domain 只在内部用于分组展示，让用户选既无意义
  // 又容易选错；改为让用户填一句分类说明，更有信息量。
  const [description, setDescription] = useState(editing?.description ?? '')
  const [parent, setParent] = useState<KnowledgeCategory | null>(
    editing ? findCategoryPath(tree, editing.parent_id ?? undefined)?.at(-1) ?? null : null,
  )
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const save = async () => {
    if (!name.trim()) return
    setBusy(true)
    setError('')
    try {
      if (editing) {
        await knowledgeApi.updateCategory(editing.id, {
          name: name.trim(),
          description: description.trim() || null,
        })
      } else {
        // domain 继承父分类，根分类回落 custom——用户不再需要理解这个概念
        await knowledgeApi.createCategory({
          name: name.trim(),
          description: description.trim() || null,
          domain: parent?.domain ?? 'custom',
          parent_id: parent?.id ?? null,
        })
      }
      await onSaved()
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof detail === 'string' && detail ? detail : isRenaming ? '重命名失败' : '分类创建失败')
    } finally {
      setBusy(false)
    }
  }

  return <div className="fixed inset-0 z-[60] grid place-items-center bg-black/70 p-4"><div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900"><header className="flex items-center justify-between border-b border-zinc-800 p-4"><h2 className="font-semibold">{isRenaming ? '重命名分类' : '新建分类'}</h2><button onClick={onClose} className="icon-button"><X size={17} /></button></header><div className="space-y-4 p-5"><Field label="分类名称"><input autoFocus className="field mt-1.5" value={name} onChange={(event) => setName(event.target.value)} placeholder={isRenaming ? undefined : '例如：雅思口语'} /></Field><Field label="分类说明"><textarea className="field mt-1.5 min-h-20 resize-y" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="简要说明这个分类放什么内容（可选）" /></Field><Field label="父分类">
        {/* 2026-09-30 改用可折叠树：原生 select 摊平后，四层路径在下拉里很难定位 */}
        <CategorySelect
          categories={tree}
          selected={parent}
          rootLabel="作为根分类"
          onSelect={setParent}
        />
      </Field>{isRenaming && <p className="text-[11px] leading-5 text-zinc-600">重命名只改名称与说明。调整层级会牵动整棵子树，暂不支持。</p>}{error && <p className="text-xs text-red-400">{error}</p>}</div><footer className="flex justify-end gap-2 border-t border-zinc-800 p-4"><button onClick={onClose} className="secondary-button">取消</button><button disabled={!name.trim() || busy} onClick={save} className="primary-button">{busy ? '保存中...' : isRenaming ? '保存' : '创建分类'}</button></footer></div></div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block text-sm text-zinc-300">{label}{children}</label> }
// interface FlatCategory { id: string; label: string; domain: string; source: KnowledgeCategory }
// 2026-09-30 下拉框改用「根 › 父 › 自身」的路径标签。
// 原来的 `— 缩进` 既不好看，也无法区分 Part 2 与 Part 3 下同名的「人物」。
// function flattenCategories(categories: KnowledgeCategory[], parents: string[] = []): FlatCategory[] {
//   return categories.flatMap((item) => {
//     const path = [...parents, item.name]
//     return [
//       { id: item.id, label: path.join(' › '), domain: item.domain, source: item },
//       ...flattenCategories(item.children, path),
//     ]
//   })
// }
