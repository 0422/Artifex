import { useEffect, useMemo, useState } from 'react'
import { BookOpen, ChevronDown, ChevronRight, Clock3, Library, MessageSquareText, Pencil, Plus, Search, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import type { KnowledgeCategory, Scenario, ScenarioDifficulty, ScenarioInput, ScenarioLanguage, ScenarioMode } from '../lib/types'
import { knowledgeApi, scenarioApi } from '../services/api'

const DOMAIN_LABEL: Record<string, string> = {
  language: '语言', history: '历史', politics: '政治', art: '艺术', film: '电影', custom: '自定义',
}
const MODE_LABEL: Record<ScenarioMode, string> = {
  role_play: '角色扮演', guided_discussion: '主题讨论', socratic_dialogue: '苏格拉底问答', debate: '观点辩论', source_analysis: '资料分析', work_analysis: '作品赏析',
}
const LANGUAGE_LABEL: Record<ScenarioLanguage, string> = { en: '英语', ja: '日语', zh: '中文' }
const DIFFICULTIES: Record<ScenarioLanguage, ScenarioDifficulty[]> = {
  en: ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
  ja: ['N5', 'N4', 'N3', 'N2', 'N1'],
  zh: ['beginner', 'intermediate', 'advanced'],
}
const DIFFICULTY_LABEL: Record<string, string> = { beginner: '入门', intermediate: '进阶', advanced: '高级' }

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
})

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
    }).catch(() => setError('知识库加载失败')).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => { void loadScenarios(selectedCategory, query) }, 250)
    return () => window.clearTimeout(timer)
  }, [query, selectedCategory]) // eslint-disable-line react-hooks/exhaustive-deps

  const categoryOptions = useMemo(() => flattenCategories(categories), [categories])

  const openEditor = (scenario?: Scenario) => {
    setError('')
    setEditor(scenario ?? 'new')
    setForm(scenario ? {
      title: scenario.title,
      description: scenario.description,
      language: scenario.language,
      difficulty: scenario.difficulty,
      domain: scenario.domain,
      scenario_mode: scenario.scenario_mode,
      estimated_minutes: scenario.estimated_minutes,
      tags: scenario.tags,
      category_ids: scenario.categories.map((category) => category.id),
    } : emptyScenario(selectedCategory?.domain, selectedCategory?.id))
  }

  const saveScenario = async () => {
    if (!form.title.trim() || !form.description.trim()) return
    try {
      const saved = editor === 'new'
        ? await scenarioApi.create(form)
        : await scenarioApi.update((editor as Scenario).id, form)
      setEditor(null)
      await Promise.all([loadCategories(), loadScenarios()])
      setSelected(saved)
    } catch {
      setError('场景保存失败，请检查输入内容')
    }
  }

  return (
    <div className="flex h-full min-h-0 bg-zinc-900">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950 lg:flex">
        <div className="flex h-14 items-center justify-between border-b border-zinc-800 px-4">
          <div><h1 className="text-sm font-semibold text-zinc-100">知识分类</h1><p className="text-xs text-zinc-500">按领域和类别浏览</p></div>
          <button title="新建分类" aria-label="新建分类" onClick={() => setCategoryEditorOpen(true)} className="icon-button"><Plus size={16} /></button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          <button onClick={() => setSelectedCategory(null)} className={`flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm ${selectedCategory === null ? 'bg-teal-950 text-teal-300' : 'text-zinc-400 hover:bg-zinc-900'}`}><Library size={16} />全部场景</button>
          <div className="mt-2 space-y-0.5">{categories.map((category) => <CategoryNode key={category.id} category={category} selectedId={selectedCategory?.id} onSelect={setSelectedCategory} />)}</div>
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-14 shrink-0 flex-wrap items-center gap-3 border-b border-zinc-800 px-4 py-2 sm:px-6">
          <div className="min-w-0 flex-1"><h1 className="truncate text-sm font-semibold text-zinc-100">{selectedCategory?.name ?? '全部场景'}</h1><p className="text-xs text-zinc-500">{loading ? '正在加载...' : `${scenarios.length} 张学习场景卡`}</p></div>
          <select className="field h-9 w-full py-1 lg:hidden" value={selectedCategory?.id ?? ''} onChange={(event) => setSelectedCategory(categoryOptions.find((item) => item.id === event.target.value)?.source ?? null)}><option value="">全部场景</option>{categoryOptions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select>
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
        {selected && <ScenarioPreview scenario={selected} onClose={() => setSelected(null)} onEdit={() => openEditor(selected)} onStart={() => navigate(`/chat?scenario=${selected.id}`)} />}
      </aside>

      {editor && <ScenarioEditor form={form} categories={categoryOptions} editing={editor !== 'new'} onChange={setForm} onClose={() => setEditor(null)} onSave={saveScenario} />}
      {categoryEditorOpen && <CategoryEditor categories={categoryOptions} selected={selectedCategory} onClose={() => setCategoryEditorOpen(false)} onSaved={async () => { setCategoryEditorOpen(false); await loadCategories() }} />}
    </div>
  )
}

function CategoryNode({ category, selectedId, onSelect }: { category: KnowledgeCategory; selectedId?: string; onSelect: (category: KnowledgeCategory) => void }) {
  const [open, setOpen] = useState(true)
  return <div><div className={`group flex items-center rounded ${selectedId === category.id ? 'bg-teal-950 text-teal-300' : 'text-zinc-400 hover:bg-zinc-900'}`}>
    <button title={open ? '收起分类' : '展开分类'} onClick={() => setOpen((value) => !value)} className={`grid h-8 w-8 place-items-center ${category.children.length ? '' : 'invisible'}`}>{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</button>
    <button onClick={() => onSelect(category)} className="flex min-w-0 flex-1 items-center justify-between py-2 pr-3 text-left text-sm"><span className="truncate">{category.name}</span>{category.card_count > 0 && <span className="text-[10px] text-zinc-600">{category.card_count}</span>}</button>
  </div>{open && category.children.length > 0 && <div className="ml-4 border-l border-zinc-800 pl-1">{category.children.map((child) => <CategoryNode key={child.id} category={child} selectedId={selectedId} onSelect={onSelect} />)}</div>}</div>
}

function ScenarioCard({ scenario, selected, onClick }: { scenario: Scenario; selected: boolean; onClick: () => void }) {
  return <button onClick={onClick} className={`min-h-44 rounded-lg border p-4 text-left transition-colors ${selected ? 'border-teal-700 bg-teal-950/30' : 'border-zinc-800 bg-zinc-950/50 hover:border-zinc-700 hover:bg-zinc-900'}`}>
    <div className="flex items-start justify-between gap-3"><span className="rounded bg-zinc-800 px-2 py-1 text-[10px] text-zinc-400">{DOMAIN_LABEL[scenario.domain] ?? scenario.domain}</span><span className="text-[10px] text-zinc-600">{MODE_LABEL[scenario.scenario_mode]}</span></div>
    <h2 className="mt-4 font-medium text-zinc-100">{scenario.title}</h2><p className="mt-2 line-clamp-3 text-xs leading-5 text-zinc-500">{scenario.description}</p>
    <div className="mt-4 flex flex-wrap items-center gap-2 text-[10px] text-zinc-500"><span>{LANGUAGE_LABEL[scenario.language]}</span><span>·</span><span>{DIFFICULTY_LABEL[scenario.difficulty] ?? scenario.difficulty}</span>{scenario.estimated_minutes && <><span>·</span><span>{scenario.estimated_minutes} 分钟</span></>}</div>
  </button>
}

function ScenarioPreview({ scenario, onClose, onEdit, onStart }: { scenario: Scenario; onClose: () => void; onEdit: () => void; onStart: () => void }) {
  return <><header className="flex h-14 items-center justify-between border-b border-zinc-800 px-4"><span className="text-sm font-semibold">场景预览</span><button onClick={onClose} title="关闭预览" className="icon-button"><X size={17} /></button></header>
    <div className="min-h-0 flex-1 overflow-y-auto p-6"><div className="flex gap-2"><span className="rounded bg-teal-950 px-2 py-1 text-xs text-teal-300">{DOMAIN_LABEL[scenario.domain] ?? scenario.domain}</span><span className="rounded bg-zinc-900 px-2 py-1 text-xs text-zinc-400">{MODE_LABEL[scenario.scenario_mode]}</span></div><h2 className="mt-5 text-xl font-semibold text-zinc-100">{scenario.title}</h2><p className="mt-3 text-sm leading-6 text-zinc-400">{scenario.description}</p>
      <dl className="mt-6 divide-y divide-zinc-800 border-y border-zinc-800 text-sm"><Info label="输出语言" value={LANGUAGE_LABEL[scenario.language]} /><Info label="难度" value={DIFFICULTY_LABEL[scenario.difficulty] ?? scenario.difficulty} /><Info label="预计时长" value={scenario.estimated_minutes ? `${scenario.estimated_minutes} 分钟` : '未设置'} /><Info label="分类" value={scenario.categories.map((item) => item.name).join(' / ') || '未分类'} /></dl>
      {scenario.tags.length > 0 && <div className="mt-6"><h3 className="text-xs text-zinc-500">主题标签</h3><div className="mt-2 flex flex-wrap gap-2">{scenario.tags.map((tag) => <span key={tag} className="rounded-full border border-zinc-700 px-2 py-1 text-xs text-zinc-400">{tag}</span>)}</div></div>}
    </div><footer className="flex gap-2 border-t border-zinc-800 p-4"><button onClick={onEdit} className="secondary-button"><Pencil size={15} />编辑</button><button onClick={onStart} className="primary-button flex-1"><MessageSquareText size={15} />开始对话</button></footer></>
}

function Info({ label, value }: { label: string; value: string }) { return <div className="flex justify-between gap-4 py-3"><dt className="text-zinc-500">{label}</dt><dd className="text-right text-zinc-300">{value}</dd></div> }

function EmptyState({ onCreate }: { onCreate: () => void }) { return <div className="mx-auto max-w-sm py-24 text-center"><BookOpen className="mx-auto text-zinc-700" size={34} /><h2 className="mt-4 font-medium text-zinc-300">这里还没有学习场景</h2><p className="mt-2 text-sm text-zinc-600">创建第一张场景卡，或切换到其他分类浏览。</p><button onClick={onCreate} className="primary-button mt-5"><Plus size={15} />新建场景</button></div> }

function ScenarioEditor({ form, categories, editing, onChange, onClose, onSave }: { form: ScenarioInput; categories: FlatCategory[]; editing: boolean; onChange: (form: ScenarioInput) => void; onClose: () => void; onSave: () => void }) {
  const language = form.language
  return <div className="fixed inset-0 z-50 flex justify-end bg-black/70"><div className="flex h-full w-full max-w-xl flex-col border-l border-zinc-700 bg-zinc-900 shadow-2xl"><header className="flex h-14 items-center justify-between border-b border-zinc-800 px-5"><h2 className="font-semibold">{editing ? '编辑学习场景' : '新建学习场景'}</h2><button onClick={onClose} className="icon-button"><X size={17} /></button></header><div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
    <Field label="场景名称"><input autoFocus className="field mt-1.5" value={form.title} onChange={(event) => onChange({ ...form, title: event.target.value })} placeholder="例如：讨论王安石变法" /></Field>
    <Field label="场景说明"><textarea className="field mt-1.5 min-h-28 resize-y" value={form.description} onChange={(event) => onChange({ ...form, description: event.target.value })} placeholder="说明学习目标、讨论背景和 AI 应如何参与" /></Field>
    <div className="grid grid-cols-2 gap-3"><Field label="领域"><select className="field mt-1.5" value={form.domain} onChange={(event) => { const domain = event.target.value; onChange({ ...emptyScenario(domain), title: form.title, description: form.description }) }}>{Object.entries(DOMAIN_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field><Field label="分类"><select className="field mt-1.5" value={form.category_ids?.[0] ?? ''} onChange={(event) => onChange({ ...form, category_ids: event.target.value ? [event.target.value] : [] })}><option value="">未分类</option>{categories.filter((item) => item.domain === form.domain).map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></Field></div>
    <div className="grid grid-cols-2 gap-3"><Field label="场景类型"><select className="field mt-1.5" value={form.scenario_mode} onChange={(event) => onChange({ ...form, scenario_mode: event.target.value as ScenarioMode })}>{Object.entries(MODE_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field><Field label="预计时长"><div className="relative"><Clock3 size={14} className="absolute left-3 top-4 text-zinc-500" /><input type="number" min="1" max="240" className="field mt-1.5 pl-9" value={form.estimated_minutes ?? ''} onChange={(event) => onChange({ ...form, estimated_minutes: Number(event.target.value) || null })} /></div></Field></div>
    <div className="grid grid-cols-2 gap-3"><Field label="输出语言"><select className="field mt-1.5" value={language} onChange={(event) => { const next = event.target.value as ScenarioLanguage; onChange({ ...form, language: next, difficulty: DIFFICULTIES[next][0] }) }}>{Object.entries(LANGUAGE_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field><Field label="难度"><select className="field mt-1.5" value={form.difficulty} onChange={(event) => onChange({ ...form, difficulty: event.target.value as ScenarioDifficulty })}>{DIFFICULTIES[language].map((value) => <option key={value} value={value}>{DIFFICULTY_LABEL[value] ?? value}</option>)}</select></Field></div>
    <Field label="标签（使用逗号分隔）"><input className="field mt-1.5" value={(form.tags ?? []).join(', ')} onChange={(event) => onChange({ ...form, tags: event.target.value.split(/[,，]/).map((tag) => tag.trim()).filter(Boolean) })} placeholder="政策, 财政, 宋代" /></Field>
  </div><footer className="flex justify-end gap-2 border-t border-zinc-800 p-4"><button onClick={onClose} className="secondary-button">取消</button><button disabled={!form.title.trim() || !form.description.trim()} onClick={onSave} className="primary-button">保存场景</button></footer></div></div>
}

function CategoryEditor({ categories, selected, onClose, onSaved }: { categories: FlatCategory[]; selected: KnowledgeCategory | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState('')
  const [domain, setDomain] = useState(selected?.domain ?? 'custom')
  const [parentId, setParentId] = useState(selected?.id ?? '')
  const [error, setError] = useState('')
  const save = async () => { try { await knowledgeApi.createCategory({ name, domain, parent_id: parentId || null }); await onSaved() } catch { setError('分类创建失败') } }
  return <div className="fixed inset-0 z-[60] grid place-items-center bg-black/70 p-4"><div className="w-full max-w-md rounded-lg border border-zinc-700 bg-zinc-900"><header className="flex items-center justify-between border-b border-zinc-800 p-4"><h2 className="font-semibold">新建分类</h2><button onClick={onClose} className="icon-button"><X size={17} /></button></header><div className="space-y-4 p-5"><Field label="分类名称"><input autoFocus className="field mt-1.5" value={name} onChange={(event) => setName(event.target.value)} /></Field><Field label="所属领域"><select className="field mt-1.5" value={domain} onChange={(event) => setDomain(event.target.value)}>{Object.entries(DOMAIN_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field><Field label="父分类"><select className="field mt-1.5" value={parentId} onChange={(event) => setParentId(event.target.value)}><option value="">作为根分类</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></Field>{error && <p className="text-xs text-red-400">{error}</p>}</div><footer className="flex justify-end gap-2 border-t border-zinc-800 p-4"><button onClick={onClose} className="secondary-button">取消</button><button disabled={!name.trim()} onClick={save} className="primary-button">创建分类</button></footer></div></div>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block text-sm text-zinc-300">{label}{children}</label> }
interface FlatCategory { id: string; label: string; domain: string; source: KnowledgeCategory }
function flattenCategories(categories: KnowledgeCategory[], depth = 0): FlatCategory[] { return categories.flatMap((item) => [{ id: item.id, label: `${'— '.repeat(depth)}${item.name}`, domain: item.domain, source: item }, ...flattenCategories(item.children, depth + 1)]) }
