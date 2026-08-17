import { lazy, Suspense, useEffect, useEffectEvent, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, CircleStop, Menu, Mic, RotateCcw, Send, Settings2, Sparkles, UserRound, Volume2, VolumeX } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'

import type { DigitalHumanMood, DigitalHumanMotion } from '../components/DigitalHumanAvatar'
import ScenarioManager from '../components/ScenarioManager'
import type { ChatMessage, ChatServerEvent, Scenario, SessionReport } from '../lib/types'
import {
  createSpeechRecognition,
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
  speakText,
  speechLocale,
  stopSpeaking,
  type BrowserSpeechRecognition,
} from '../services/browserSpeech'
import { ChatSocket } from '../services/chatSocket'
import { useAuthStore } from '../stores/authStore'

type SessionState = 'idle' | 'starting' | 'active' | 'ending' | 'reporting'

const MOOD_LABEL: Record<DigitalHumanMood, string> = {
  neutral: '准备好了', happy: '做得不错', thinking: '正在思考', relaxed: '正在倾听', sad: '再试一次',
}
const MOODS = Object.keys(MOOD_LABEL) as DigitalHumanMood[]
const MOTION_LABEL: Record<DigitalHumanMotion, string> = {
  auto: '自动', showcase: '全身展示', greeting: '问候', peace: 'V 手势', shoot: '射击', spin: '旋转', modelPose: '模特姿势', squat: '屈伸',
}
const LANGUAGE_LABEL = { en: '英语', ja: '日语', zh: '中文' } as const
const AVATAR_WIDTH_KEY = 'artifex_avatar_panel_width'
const AVATAR_MIN_WIDTH = 0
const AVATAR_COLLAPSE_THRESHOLD = 180
const AVATAR_DEFAULT_WIDTH = 360
const AVATAR_MAX_WIDTH = 1200
const CHAT_MIN_WIDTH = 360
const SCENARIO_PANEL_WIDTH = 288
const AVATAR_SETTINGS_WIDTH = 320
const AVATAR_VIEW_SCALE_MIN = 0.45
const AVATAR_VIEW_SCALE_MAX = 1.2
const AVATAR_VIEW_SCALE_DEFAULT = 0.54
const AVATAR_VIEW_SCALE_KEY = 'artifex_avatar_view_scale'
const AVATAR_VIEW_ROTATION_KEY = 'artifex_avatar_view_rotation'
const DigitalHumanAvatar = lazy(() => import('../components/DigitalHumanAvatar'))

export default function ChatPage() {
  const [searchParams] = useSearchParams()
  const requestedScenarioId = searchParams.get('scenario')
  const token = useAuthStore((s) => s.accessToken)
  const [selected, setSelected] = useState<Scenario | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [sessionState, setSessionState] = useState<SessionState>('idle')
  const [socketState, setSocketState] = useState<'connecting' | 'open' | 'closed'>('closed')
  const [authenticated, setAuthenticated] = useState(false)
  const [mood, setMood] = useState<DigitalHumanMood>('neutral')
  const [report, setReport] = useState<SessionReport | null>(null)
  const [error, setError] = useState('')
  const [scenarioOpen, setScenarioOpen] = useState(true)
  const [avatarWidth, setAvatarWidth] = useState(() => {
    const stored = Number(localStorage.getItem(AVATAR_WIDTH_KEY))
    return Number.isFinite(stored) && stored >= AVATAR_MIN_WIDTH && stored <= AVATAR_MAX_WIDTH ? stored : AVATAR_DEFAULT_WIDTH
  })
  const [avatarResizing, setAvatarResizing] = useState(false)
  const [avatarMobileOpen, setAvatarMobileOpen] = useState(false)
  const [avatarViewScale, setAvatarViewScale] = useState(() => {
    const stored = Number(localStorage.getItem(AVATAR_VIEW_SCALE_KEY))
    return Number.isFinite(stored) && stored >= AVATAR_VIEW_SCALE_MIN && stored <= AVATAR_VIEW_SCALE_MAX
      ? stored
      : AVATAR_VIEW_SCALE_DEFAULT
  })
  const [avatarViewRotation, setAvatarViewRotation] = useState(() => {
    const stored = Number(localStorage.getItem(AVATAR_VIEW_ROTATION_KEY))
    return Number.isFinite(stored) ? stored : 0
  })
  const [showEndHint, setShowEndHint] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [speechOutputEnabled, setSpeechOutputEnabled] = useState(true)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [mouthLevel, setMouthLevel] = useState(0)
  const [avatarSettingsOpen, setAvatarSettingsOpen] = useState(false)
  const [avatarMotion, setAvatarMotion] = useState<DigitalHumanMotion>('auto')
  const socketRef = useRef<ChatSocket | null>(null)
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const chatLayoutRef = useRef<HTMLDivElement>(null)
  const avatarWidthRef = useRef(avatarWidth)
  const speechInputSupported = isSpeechRecognitionSupported()
  const speechOutputSupported = isSpeechSynthesisSupported()
  const avatarOpen = avatarWidth >= AVATAR_COLLAPSE_THRESHOLD

  const updateAvatarViewScale = (scale: number) => {
    const next = Math.min(AVATAR_VIEW_SCALE_MAX, Math.max(AVATAR_VIEW_SCALE_MIN, scale))
    setAvatarViewScale(next)
    localStorage.setItem(AVATAR_VIEW_SCALE_KEY, String(next))
  }

  const updateAvatarViewRotation = (rotation: number) => {
    const next = Math.atan2(Math.sin(rotation), Math.cos(rotation))
    setAvatarViewRotation(next)
    localStorage.setItem(AVATAR_VIEW_ROTATION_KEY, String(next))
  }

  const getAvatarMaxWidth = () => {
    const layoutWidth = chatLayoutRef.current?.clientWidth ?? window.innerWidth
    const scenarioWidth = window.innerWidth >= 1024 && scenarioOpen ? SCENARIO_PANEL_WIDTH : 0
    const settingsWidth = window.innerWidth >= 1280 && avatarSettingsOpen ? AVATAR_SETTINGS_WIDTH : 0
    return Math.min(
      AVATAR_MAX_WIDTH,
      Math.max(AVATAR_DEFAULT_WIDTH, layoutWidth - scenarioWidth - settingsWidth - CHAT_MIN_WIDTH),
    )
  }

  const updateAvatarWidth = (width: number) => {
    const next = Math.min(getAvatarMaxWidth(), Math.max(AVATAR_MIN_WIDTH, width))
    avatarWidthRef.current = next
    setAvatarWidth(next)
  }

  const commitAvatarWidth = (width = avatarWidthRef.current) => {
    const next = width < AVATAR_COLLAPSE_THRESHOLD
      ? AVATAR_MIN_WIDTH
      : Math.min(getAvatarMaxWidth(), Math.max(260, width))
    avatarWidthRef.current = next
    setAvatarWidth(next)
    localStorage.setItem(AVATAR_WIDTH_KEY, String(next))
    if (next === AVATAR_MIN_WIDTH) setAvatarSettingsOpen(false)
  }

  const clampAvatarWidthToLayout = useEffectEvent(() => {
    if (window.innerWidth < 1280 || avatarWidthRef.current < AVATAR_COLLAPSE_THRESHOLD) return
    const maxWidth = getAvatarMaxWidth()
    if (avatarWidthRef.current > maxWidth) commitAvatarWidth(maxWidth)
  })

  useEffect(() => {
    const layout = chatLayoutRef.current
    if (!layout) return
    const observer = new ResizeObserver(() => clampAvatarWidthToLayout())
    observer.observe(layout)
    clampAvatarWidthToLayout()
    return () => observer.disconnect()
  }, [scenarioOpen, avatarSettingsOpen])

  const speakResponse = (content: string) => {
    if (!speechOutputEnabled || !speechOutputSupported) return
    speakText(content, selected?.language, {
      onSpeakingChange: setIsSpeaking,
      onMouthLevelChange: setMouthLevel,
    })
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, report, sessionState])

  const handleEvent = useEffectEvent((event: ChatServerEvent) => {
    if (event.type === 'authenticated') {
      setAuthenticated(true)
      setError((current) => current === '无法连接到对话服务' ? '' : current)
      return
    }
    if (event.type === 'session_started') {
      setSessionState('active')
      setMood('relaxed')
      return
    }
    if (event.type === 'ai_response') {
      setMessages((current) => [...current, { id: event.message_id, role: 'assistant', content: event.content, createdAt: event.created_at, degraded: event.degraded }])
      speakResponse(event.content)
      setMood('happy')
      window.setTimeout(() => setMood('relaxed'), 1200)
      return
    }
    if (event.type === 'correction') {
      setMessages((current) => {
        const index = current.findLastIndex((message) => message.role === 'user' && !message.correction)
        return current.map((message, messageIndex) => messageIndex === index ? { ...message, correction: event } : message)
      })
      return
    }
    if (event.type === 'session_ended') {
      setSessionState('reporting')
      setMood('thinking')
      return
    }
    if (event.type === 'report_generating') {
      setSessionState('reporting')
      return
    }
    if (event.type === 'session_report') {
      setReport(event.report)
      setSessionState('idle')
      setMood('happy')
      return
    }
    if (event.type === 'error') {
      setError(event.message)
      if (!event.recoverable) setSessionState('idle')
    }
  })

  useEffect(() => {
    if (!token) return
    const socket = new ChatSocket(handleEvent, (state) => {
      setSocketState(state)
      if (state !== 'open') setAuthenticated(false)
    })
    socketRef.current = socket
    socket.connect(token)
    return () => socket.close()
  }, [token])

  useEffect(() => {
    if (sessionState !== 'active') return
    const timer = window.setTimeout(() => setShowEndHint(true), 180_000)
    return () => window.clearTimeout(timer)
  }, [sessionState])

  useEffect(() => () => {
    recognitionRef.current?.abort()
    stopSpeaking()
  }, [])

  useEffect(() => {
    if (sessionState === 'active') return
    recognitionRef.current?.abort()
    recognitionRef.current = null
    stopSpeaking()
  }, [sessionState])

  const start = () => {
    if (!selected || !authenticated) return
    stopSpeaking()
    setIsSpeaking(false)
    setMouthLevel(0)
    setIsListening(false)
    setMessages([])
    setReport(null)
    setError('')
    setShowEndHint(false)
    setSessionState('starting')
    setMood('thinking')
    socketRef.current?.startSession(selected.id, selected.difficulty)
  }

  const send = () => {
    const content = draft.trim()
    if (!content || sessionState !== 'active') return
    recognitionRef.current?.stop()
    const id = crypto.randomUUID()
    setMessages((current) => [...current, { id, role: 'user', content, createdAt: new Date().toISOString() }])
    setDraft('')
    setMood('thinking')
    socketRef.current?.sendText(content)
  }

  const end = () => {
    if (!window.confirm('确定结束本次会话并生成学习报告吗？')) return
    recognitionRef.current?.abort()
    stopSpeaking()
    setIsListening(false)
    setIsSpeaking(false)
    setMouthLevel(0)
    setSessionState('ending')
    setMood('thinking')
    socketRef.current?.endSession()
  }

  const unavailable = !authenticated || socketState !== 'open'

  const toggleListening = () => {
    if (isListening) {
      recognitionRef.current?.stop()
      return
    }

    const recognition = createSpeechRecognition()
    if (!recognition) {
      setError('当前浏览器不支持语音识别，请使用最新版 Chrome 或 Edge。')
      return
    }

    stopSpeaking()
    setIsSpeaking(false)
    setMouthLevel(0)
    setError('')
    const existingDraft = draft.trimEnd()
    recognition.lang = speechLocale(selected?.language)
    recognition.continuous = false
    recognition.interimResults = true
    recognition.maxAlternatives = 1
    recognition.onstart = () => {
      setIsListening(true)
      setMood('relaxed')
    }
    recognition.onresult = (event) => {
      let transcript = ''
      for (let index = 0; index < event.results.length; index += 1) {
        transcript += event.results[index][0]?.transcript ?? ''
      }
      const separator = existingDraft && transcript ? ' ' : ''
      setDraft(`${existingDraft}${separator}${transcript}`)
    }
    recognition.onerror = (event) => {
      if (event.error === 'aborted' || event.error === 'no-speech') return
      const message = event.error === 'not-allowed' || event.error === 'service-not-allowed'
        ? '麦克风权限被拒绝，请在浏览器设置中允许访问麦克风。'
        : event.error === 'audio-capture'
          ? '没有检测到可用麦克风。'
          : '语音识别失败，请检查网络后重试。'
      setError(message)
    }
    recognition.onend = () => {
      recognitionRef.current = null
      setIsListening(false)
    }
    recognitionRef.current = recognition

    try {
      recognition.start()
    } catch {
      recognitionRef.current = null
      setIsListening(false)
      setError('无法启动语音识别，请稍后重试。')
    }
  }

  const toggleSpeechOutput = () => {
    if (!speechOutputSupported) {
      setError('当前浏览器不支持语音播放。')
      return
    }
    if (speechOutputEnabled) {
      stopSpeaking()
      setIsSpeaking(false)
      setMouthLevel(0)
    }
    setSpeechOutputEnabled((enabled) => !enabled)
  }

  return (
    <div ref={chatLayoutRef} className="relative flex h-full min-h-0 overflow-hidden bg-zinc-950">
      {scenarioOpen && <button aria-label="关闭场景" className="fixed inset-x-0 bottom-14 top-0 z-30 bg-black/70 lg:hidden" onClick={() => setScenarioOpen(false)} />}
      <div className={`${scenarioOpen ? 'translate-x-0 lg:w-72' : '-translate-x-full lg:w-0 lg:translate-x-0'} fixed bottom-14 left-0 top-0 z-40 w-[min(20rem,88vw)] shrink-0 overflow-hidden transition-[transform,width] lg:static lg:z-auto lg:block lg:h-full`}>
        <div className="relative h-full w-72">
          <ScenarioManager requestedId={requestedScenarioId} selectedId={selected?.id ?? null} disabled={sessionState !== 'idle'} onClose={() => setScenarioOpen(false)} onSelect={(scenario) => { setSelected(scenario); if (window.innerWidth < 1024) setScenarioOpen(false) }} />
        </div>
      </div>

      <main className="flex min-w-0 flex-1 flex-col bg-zinc-900">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-800 px-3 sm:px-5">
          <div className="flex min-w-0 items-center gap-2">
            <span className="lg:hidden"><button title="选择场景" onClick={() => setScenarioOpen(true)} className="icon-button"><Menu size={17} /></button></span>
            <span className="hidden lg:block"><button title={scenarioOpen ? '收起场景' : '展开场景'} onClick={() => setScenarioOpen((v) => !v)} className="icon-button">
              {scenarioOpen ? <ChevronLeft size={17} /> : <ChevronRight size={17} />}
            </button></span>
            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold text-zinc-100">{selected?.title ?? '情境对话'}</h1>
              <p className="truncate text-xs text-zinc-500">{selected ? `${LANGUAGE_LABEL[selected.language]} · ${selected.difficulty}` : '请选择练习场景'}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={avatarOpen ? 'xl:hidden' : ''}><button title="打开对话伙伴" aria-label="打开对话伙伴" onClick={() => {
              if (window.innerWidth >= 1280) commitAvatarWidth(AVATAR_DEFAULT_WIDTH)
              else setAvatarMobileOpen(true)
            }} className="icon-button"><UserRound size={17} /></button></div>
            <span className={`hidden text-xs sm:inline ${socketState === 'open' && authenticated ? 'text-emerald-400' : 'text-amber-400'}`}>
              {socketState === 'open' && authenticated ? '对话服务在线' : socketState === 'connecting' ? '正在连接' : '服务未连接'}
            </span>
            <button disabled={!selected || unavailable || sessionState !== 'idle'} onClick={start} style={{ display: sessionState === 'active' || sessionState === 'ending' ? 'none' : undefined }} className="primary-button"><Sparkles size={15} /><span>开始练习</span></button>
            <button disabled={sessionState === 'ending'} onClick={end} style={{ display: sessionState === 'active' || sessionState === 'ending' ? undefined : 'none' }} className="secondary-button text-red-300"><CircleStop size={15} /><span>结束会话</span></button>
          </div>
        </header>

        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex min-h-full max-w-3xl flex-col px-4 py-6 sm:px-8">
            {messages.length === 0 && !report && (
              <div className="m-auto max-w-md py-12 text-center">
                <Sparkles className="mx-auto mb-4 text-teal-400" size={30} />
                <h2 className="text-lg font-semibold text-zinc-100">{selected ? selected.title : '选择一个练习场景'}</h2>
                <p className="mt-2 text-sm leading-6 text-zinc-500">{selected?.description ?? '从场景列表中选择情境，AI 会扮演对话角色并在过程中给出纠错建议。'}</p>
              </div>
            )}
            <div className="space-y-5">
              {messages.map((message) => (
                <article key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className="max-w-[88%] sm:max-w-[75%]">
                    <div className={`rounded-lg px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'bg-teal-700 text-white' : 'border border-zinc-700 bg-zinc-800 text-zinc-100'}`}>
                      {message.role === 'assistant' ? <TypewriterText text={message.content} /> : message.content}
                    </div>
                    {message.degraded && <p className="mt-1 text-xs text-amber-400">当前为备用回复</p>}
                    {message.correction && (
                      <div className={`mt-2 border-l-2 px-3 py-2 text-xs leading-5 ${message.correction.severity === 'major' ? 'border-red-400 bg-red-950/30' : 'border-amber-400 bg-amber-950/20'}`}>
                        <p className="text-zinc-400 line-through">{message.correction.original}</p>
                        <p className="font-medium text-emerald-300">{message.correction.corrected}</p>
                        <p className="mt-1 text-zinc-400">{message.correction.explanation}</p>
                      </div>
                    )}
                  </div>
                </article>
              ))}
            </div>
            {(sessionState === 'starting' || sessionState === 'reporting' || sessionState === 'ending') && (
              <div className="my-5 flex items-center gap-2 text-sm text-zinc-500"><span className="h-2 w-2 animate-pulse rounded-full bg-teal-400" />{sessionState === 'reporting' ? '正在生成学习报告...' : 'AI 正在准备...'}</div>
            )}
            {showEndHint && sessionState === 'active' && <div className="my-5 flex items-center justify-between gap-4 border-y border-teal-900 bg-teal-950/30 px-4 py-3 text-sm text-teal-200"><span>已练习 3 分钟，可以结束并生成学情报告。</span><button onClick={end} className="secondary-button">结束会话</button></div>}
            {report && <ReportPanel report={report} />}
          </div>
        </div>

        {error && <div className="border-t border-red-900/60 bg-red-950/40 px-5 py-2 text-xs text-red-300">{error}</div>}
        <footer className="shrink-0 border-t border-zinc-800 bg-zinc-950 p-3 sm:p-4">
          <div className="mx-auto flex max-w-3xl items-end gap-2">
            <button
              disabled={sessionState !== 'active' || !speechInputSupported}
              title={!speechInputSupported ? '当前浏览器不支持语音识别' : isListening ? '停止语音输入' : '开始语音输入'}
              aria-label={isListening ? '停止语音输入' : '开始语音输入'}
              aria-pressed={isListening}
              onClick={toggleListening}
              className={`icon-button h-10 w-10 ${isListening ? 'animate-pulse bg-red-950 text-red-300 hover:bg-red-900' : ''}`}
            >
              <Mic size={18} />
            </button>
            <textarea value={draft} disabled={sessionState !== 'active'} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
            }} rows={1} className="field min-w-0 max-h-32 min-h-10 flex-1 resize-none py-2.5" placeholder={isListening ? '正在聆听...' : sessionState === 'active' ? '输入你的回答...' : '开始练习后即可发送消息'} />
            <button
              disabled={!speechOutputSupported}
              title={speechOutputEnabled ? '关闭 AI 语音' : '开启 AI 语音'}
              aria-label={speechOutputEnabled ? '关闭 AI 语音' : '开启 AI 语音'}
              aria-pressed={speechOutputEnabled}
              onClick={toggleSpeechOutput}
              className={`icon-button h-10 w-10 ${isSpeaking ? 'animate-pulse bg-teal-950 text-teal-300' : speechOutputEnabled ? 'text-teal-400' : ''}`}
            >
              {speechOutputEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
            </button>
            <button disabled={!draft.trim() || sessionState !== 'active'} title="发送" onClick={send} className="primary-button h-10 w-10 justify-center px-0"><Send size={17} /></button>
          </div>
        </footer>
      </main>

      <aside style={avatarMobileOpen ? undefined : { width: avatarWidth }} className={`${avatarMobileOpen ? 'fixed inset-0 z-50 flex w-full' : 'hidden'} relative shrink-0 flex-col bg-zinc-950 xl:relative xl:z-auto xl:flex ${avatarOpen || avatarMobileOpen ? 'border-l border-zinc-800' : 'overflow-hidden border-l-0'} ${avatarResizing ? '' : 'transition-[width]'}`}>
        {avatarOpen && <div
          role="separator"
          aria-label="调整对话伙伴宽度"
          aria-orientation="vertical"
          aria-valuemin={AVATAR_MIN_WIDTH}
          aria-valuemax={AVATAR_MAX_WIDTH}
          aria-valuenow={Math.round(avatarWidth)}
          tabIndex={0}
          title="拖动调整对话伙伴宽度"
          className="group absolute inset-y-0 -left-1 z-50 hidden w-2 cursor-col-resize touch-none outline-none xl:block"
          onPointerDown={(event) => {
            event.currentTarget.setPointerCapture(event.pointerId)
            setAvatarResizing(true)
            document.body.style.cursor = 'col-resize'
            document.body.style.userSelect = 'none'
          }}
          onPointerMove={(event) => {
            if (!event.currentTarget.hasPointerCapture(event.pointerId)) return
            updateAvatarWidth(window.innerWidth - event.clientX - (avatarSettingsOpen ? 320 : 0))
          }}
          onPointerUp={(event) => {
            if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
            setAvatarResizing(false)
            document.body.style.cursor = ''
            document.body.style.userSelect = ''
            commitAvatarWidth()
          }}
          onPointerCancel={() => {
            setAvatarResizing(false)
            document.body.style.cursor = ''
            document.body.style.userSelect = ''
            commitAvatarWidth()
          }}
          onKeyDown={(event) => {
            if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return
            event.preventDefault()
            const next = event.key === 'ArrowRight'
              ? Math.max(AVATAR_MIN_WIDTH, avatarWidth - 16)
              : avatarOpen ? Math.min(getAvatarMaxWidth(), avatarWidth + 16) : AVATAR_DEFAULT_WIDTH
            updateAvatarWidth(next)
            commitAvatarWidth(next)
          }}
        >
          <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-transparent transition-colors group-hover:bg-teal-500 group-focus:bg-teal-500" />
        </div>}
        {(avatarOpen || avatarMobileOpen) && <div className="flex h-14 items-center border-b border-zinc-800 px-3">
          {(avatarOpen || avatarMobileOpen) && <span className="text-sm font-medium text-zinc-300">对话伙伴</span>}
          <div className="ml-auto flex items-center gap-1">
            {(avatarOpen || avatarMobileOpen) && <button title={avatarSettingsOpen ? '收起数字人设置' : '展开数字人设置'} aria-label={avatarSettingsOpen ? '收起数字人设置' : '展开数字人设置'} onClick={() => setAvatarSettingsOpen((current) => !current)} className={`icon-button ${avatarSettingsOpen ? 'bg-zinc-800 text-teal-300' : ''}`}><Settings2 size={17} /></button>}
            <button title={avatarOpen || avatarMobileOpen ? '收起伙伴面板' : '展开伙伴面板'} aria-label={avatarOpen || avatarMobileOpen ? '收起伙伴面板' : '展开伙伴面板'} onClick={() => {
              if (window.innerWidth >= 1280) commitAvatarWidth(avatarOpen ? AVATAR_MIN_WIDTH : AVATAR_DEFAULT_WIDTH)
              else {
                setAvatarMobileOpen(false)
                setAvatarSettingsOpen(false)
              }
            }} className="icon-button">{avatarOpen || avatarMobileOpen ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}</button>
          </div>
        </div>}
        {(avatarOpen || avatarMobileOpen) && (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="relative min-h-80 flex-1">
              <Suspense fallback={<div className="flex h-full items-center justify-center"><span className="h-2 w-2 animate-pulse rounded-full bg-teal-400" /></div>}>
                <DigitalHumanAvatar mood={mood} isSpeaking={isSpeaking} mouthLevel={mouthLevel} motion={avatarMotion} viewScale={avatarViewScale} onViewScaleChange={updateAvatarViewScale} viewRotation={avatarViewRotation} onViewRotationChange={updateAvatarViewRotation} />
              </Suspense>
              <div className="pointer-events-none absolute inset-x-0 bottom-5 text-center">
                <h2 className="font-semibold text-zinc-100 drop-shadow">Aoi</h2>
                <p className="mt-1 text-sm text-teal-300 drop-shadow">{MOOD_LABEL[mood]}</p>
              </div>
            </div>
          </div>
        )}
      </aside>

      <aside className={`${avatarSettingsOpen ? 'flex' : 'hidden'} fixed inset-y-0 right-0 z-[60] w-[min(20rem,78vw)] shrink-0 flex-col border-l border-zinc-700 bg-zinc-900 shadow-2xl xl:static xl:z-auto xl:w-80 xl:shadow-none`}>
        <div className="flex h-14 shrink-0 items-center border-b border-zinc-700 px-3">
          <div><h2 className="text-sm font-semibold text-zinc-100">数字人设置</h2><p className="text-[10px] text-zinc-500">表情、语音与 VRMA 动作</p></div>
          <button title="收起数字人设置" aria-label="收起数字人设置" onClick={() => setAvatarSettingsOpen(false)} className="icon-button ml-auto"><ChevronRight size={17} /></button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-5">
            <section>
              <div className="flex items-center justify-between gap-3">
                <div><h3 className="text-sm font-medium text-zinc-200">模型视图</h3><p className="mt-1 text-[11px] text-zinc-600">缩放与观察角度</p></div>
                <button title="恢复默认视图" aria-label="恢复默认视图" onClick={() => { updateAvatarViewScale(AVATAR_VIEW_SCALE_DEFAULT); updateAvatarViewRotation(0) }} className="icon-button"><RotateCcw size={15} /></button>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <input
                  type="range"
                  min={AVATAR_VIEW_SCALE_MIN}
                  max={AVATAR_VIEW_SCALE_MAX}
                  step="0.01"
                  value={avatarViewScale}
                  onChange={(event) => updateAvatarViewScale(Number(event.target.value))}
                  aria-label="数字人视图缩放"
                  className="min-w-0 flex-1 accent-teal-500"
                />
                <output className="w-10 text-right text-xs tabular-nums text-zinc-400">{Math.round(avatarViewScale * 100)}%</output>
              </div>
            </section>

            <section className="mt-5 border-t border-zinc-800 pt-4">
              <h3 className="text-sm font-medium text-zinc-200">表情系统</h3>
              <div className="mt-3 flex flex-wrap gap-2">{MOODS.map((item) => <button key={item} onClick={() => setMood(item)} className={`rounded px-2.5 py-1.5 text-xs transition-colors ${item === mood ? 'bg-teal-950 text-teal-300' : 'bg-zinc-950 text-zinc-500 hover:text-zinc-300'}`}>{MOOD_LABEL[item]}</button>)}</div>
            </section>

            <section className="mt-5 border-t border-zinc-800 pt-4">
              <h3 className="text-sm font-medium text-zinc-200">语音</h3>
              <div className="mt-2 space-y-1 text-xs leading-5 text-zinc-500"><p>语音输入：{speechInputSupported ? isListening ? '正在聆听' : '可用' : '当前浏览器不支持'}</p><p>AI 语音：{speechOutputSupported ? speechOutputEnabled ? isSpeaking ? '正在播放' : '已开启' : '已关闭' : '当前浏览器不支持'}</p></div>
              <button disabled={!speechOutputSupported} onClick={toggleSpeechOutput} title={speechOutputEnabled ? '关闭 AI 语音' : '开启 AI 语音'} className="secondary-button mt-3">{speechOutputEnabled ? <Volume2 size={15} /> : <VolumeX size={15} />}{speechOutputEnabled ? '关闭语音' : '开启语音'}</button>
            </section>

            <section className="mt-5 border-t border-zinc-800 pt-4">
              <h3 className="text-sm font-medium text-zinc-200">VRMA 动作</h3>
              <div className="mt-2 grid grid-cols-4 gap-2">{(Object.keys(MOTION_LABEL) as DigitalHumanMotion[]).map((motion) => <button key={motion} onClick={() => setAvatarMotion(motion)} className={`rounded px-2 py-2 text-xs transition-colors ${avatarMotion === motion ? 'bg-teal-950 text-teal-300 ring-1 ring-teal-700' : 'bg-zinc-950 text-zinc-500 hover:text-zinc-300'}`}>{MOTION_LABEL[motion]}</button>)}</div>
              <p className="mt-2 text-[11px] leading-5 text-zinc-600">自动模式使用模特姿势待机，AI 朗读时切换全身展示，积极反馈时切换问候。</p>
              <p className="mt-3 text-[10px] leading-4 text-zinc-600">Animation credits to pixiv Inc.'s VRoid Project</p>
            </section>
        </div>
      </aside>
    </div>
  )
}

function ReportPanel({ report }: { report: SessionReport }) {
  return (
    <section className="mt-8 border-t border-zinc-700 pt-6">
      <div className="flex items-end justify-between gap-4">
        <div><p className="text-xs text-zinc-500">本次练习</p><h2 className="mt-1 text-lg font-semibold text-zinc-100">学习报告</h2></div>
        <div className="text-right"><span className="text-3xl font-semibold text-teal-300">{report.performance_score ?? '--'}</span><span className="text-xs text-zinc-500"> / 100</span></div>
      </div>
      <p className="mt-4 text-sm leading-6 text-zinc-300">{report.summary}</p>
      {report.insufficient_data && <p className="mt-3 text-sm text-amber-300">对话内容较少，本报告仅供参考。</p>}
      {report.weak_points.length > 0 && (
        <div className="mt-6"><h3 className="text-sm font-medium text-zinc-200">需要加强</h3><div className="mt-3 divide-y divide-zinc-800 border-y border-zinc-800">
          {report.weak_points.map((point) => <div key={point.tag} className="py-4"><div className="flex gap-2"><span className="rounded bg-amber-950 px-2 py-0.5 text-xs text-amber-300">{point.category}</span><p className="text-sm text-zinc-200">{point.description}</p></div><p className="mt-2 text-xs text-zinc-500">示例：{point.example}</p><p className="mt-1 text-xs text-teal-300">建议：{point.suggestion}</p></div>)}
        </div></div>
      )}
      <div className="mt-6"><h3 className="text-sm font-medium text-zinc-200">下一步建议</h3><ul className="mt-2 space-y-2 text-sm text-zinc-400">{report.suggestions.map((item, index) => <li key={index} className="flex gap-2"><span className="text-teal-400">{index + 1}.</span>{item}</li>)}</ul></div>
    </section>
  )
}

function TypewriterText({ text }: { text: string }) {
  const [length, setLength] = useState(0)

  useEffect(() => {
    const step = Math.max(1, Math.ceil(text.length / 80))
    const timer = window.setInterval(() => setLength((current) => {
      if (current >= text.length) {
        window.clearInterval(timer)
        return current
      }
      return Math.min(text.length, current + step)
    }), 22)
    return () => window.clearInterval(timer)
  }, [text])

  return <>{text.slice(0, length)}{length < text.length && <span className="animate-pulse text-teal-300">|</span>}</>
}
