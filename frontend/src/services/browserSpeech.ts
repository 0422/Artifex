import type { ScenarioLanguage } from '../lib/types'

interface BrowserSpeechRecognitionAlternative {
  transcript: string
}

interface BrowserSpeechRecognitionResult {
  readonly isFinal: boolean
  readonly length: number
  item(index: number): BrowserSpeechRecognitionAlternative
  [index: number]: BrowserSpeechRecognitionAlternative
}

interface BrowserSpeechRecognitionResultList {
  readonly length: number
  item(index: number): BrowserSpeechRecognitionResult
  [index: number]: BrowserSpeechRecognitionResult
}

export interface BrowserSpeechRecognitionEvent extends Event {
  readonly resultIndex: number
  readonly results: BrowserSpeechRecognitionResultList
}

export interface BrowserSpeechRecognitionErrorEvent extends Event {
  readonly error: string
}

export interface BrowserSpeechRecognition {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onstart: (() => void) | null
  onend: (() => void) | null
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null
  start(): void
  stop(): void
  abort(): void
}

type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition

export interface SpeechPlaybackCallbacks {
  onSpeakingChange: (speaking: boolean) => void
  onMouthLevelChange?: (level: number) => void
}

let currentUtterance: SpeechSynthesisUtterance | null = null
let currentUtteranceTimeout: number | null = null
let mouthAnimationFrame = 0
let playbackSession = 0
let playbackStarted = false
let mouthLevel = 0
let mouthPulse = 0
let lastBoundaryAt = 0
let activeCallbacks: SpeechPlaybackCallbacks | null = null

const speechWindow = window as typeof window & {
  SpeechRecognition?: BrowserSpeechRecognitionConstructor
  webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor
}

export function speechLocale(language: ScenarioLanguage | undefined): string {
  if (language === 'ja') return 'ja-JP'
  if (language === 'zh') return 'zh-CN'
  return 'en-US'
}

export function createSpeechRecognition(): BrowserSpeechRecognition | null {
  const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition
  return Recognition ? new Recognition() : null
}

export function isSpeechRecognitionSupported(): boolean {
  return Boolean(speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition)
}

export function isSpeechSynthesisSupported(): boolean {
  return 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window
}

export function splitSpeechSentences(text: string): string[] {
  const sentences: string[] = []
  let buffer = ''
  for (const character of text.trim()) {
    buffer += character
    if (/[。！？!?；;\n….]/.test(character)) {
      if (buffer.trim()) sentences.push(buffer.trim())
      buffer = ''
      continue
    }
    if (buffer.length >= 120) {
      const commaIndex = Math.max(buffer.lastIndexOf('，'), buffer.lastIndexOf(','))
      const cutIndex = commaIndex > 30 ? commaIndex + 1 : buffer.length
      sentences.push(buffer.slice(0, cutIndex).trim())
      buffer = buffer.slice(cutIndex)
    }
  }
  if (buffer.trim()) sentences.push(buffer.trim())

  const merged: string[] = []
  for (const sentence of sentences) {
    const previous = merged.at(-1)
    if (previous && (sentence.length < 6 || previous.length < 6)) merged[merged.length - 1] += sentence
    else merged.push(sentence)
  }
  while (merged.length > 10) {
    const compacted: string[] = []
    for (let index = 0; index < merged.length; index += 2) compacted.push(merged[index] + (merged[index + 1] ?? ''))
    merged.splice(0, merged.length, ...compacted)
  }
  return merged
}

function clearUtterance(): void {
  if (currentUtteranceTimeout !== null) {
    window.clearTimeout(currentUtteranceTimeout)
    currentUtteranceTimeout = null
  }
  if (!currentUtterance) return
  currentUtterance.onstart = null
  currentUtterance.onboundary = null
  currentUtterance.onend = null
  currentUtterance.onerror = null
  currentUtterance = null
}

function stopMouthAnimation(): void {
  if (mouthAnimationFrame) window.cancelAnimationFrame(mouthAnimationFrame)
  mouthAnimationFrame = 0
  mouthLevel = 0
  mouthPulse = 0
  activeCallbacks?.onMouthLevelChange?.(0)
}

function startMouthAnimation(session: number): void {
  if (mouthAnimationFrame) return
  const animate = (now: number) => {
    if (session !== playbackSession) return
    const boundaryActive = now - lastBoundaryAt < 260
    const fallback = currentUtterance
      ? 0.12 + Math.abs(Math.sin(now * 0.011)) * 0.3 + Math.abs(Math.sin(now * 0.0047)) * 0.1
      : 0
    const target = boundaryActive ? Math.max(fallback, mouthPulse) : fallback
    mouthLevel += (target - mouthLevel) * (target > mouthLevel ? 0.58 : 0.24)
    mouthPulse *= 0.84
    activeCallbacks?.onMouthLevelChange?.(Math.min(1, Math.max(0, mouthLevel)))
    mouthAnimationFrame = window.requestAnimationFrame(animate)
  }
  mouthAnimationFrame = window.requestAnimationFrame(animate)
}

function finishPlayback(session: number): void {
  if (session !== playbackSession) return
  clearUtterance()
  stopMouthAnimation()
  if (playbackStarted) activeCallbacks?.onSpeakingChange(false)
  playbackStarted = false
  activeCallbacks = null
}

export function stopSpeaking(): void {
  playbackSession += 1
  clearUtterance()
  stopMouthAnimation()
  if (playbackStarted) activeCallbacks?.onSpeakingChange(false)
  playbackStarted = false
  activeCallbacks = null
  if (isSpeechSynthesisSupported()) window.speechSynthesis.cancel()
}

export function speakText(
  text: string,
  language: ScenarioLanguage | undefined,
  callbacks: SpeechPlaybackCallbacks,
): void {
  if (!isSpeechSynthesisSupported()) return

  stopSpeaking()
  const chunks = splitSpeechSentences(text)
  if (!chunks.length) return
  const session = ++playbackSession
  const locale = speechLocale(language)
  const languagePrefix = locale.slice(0, 2).toLowerCase()
  activeCallbacks = callbacks
  let chunkIndex = 0

  const speakNext = () => {
    if (session !== playbackSession) return
    const chunk = chunks[chunkIndex]
    if (!chunk) {
      finishPlayback(session)
      return
    }

    const voices = window.speechSynthesis.getVoices()
    const matchingVoices = voices.filter((candidate) => candidate.lang.toLowerCase().startsWith(languagePrefix))
    const voice = matchingVoices.find((candidate) => candidate.localService) ?? matchingVoices[0]
    const utterance = new SpeechSynthesisUtterance(chunk)
    currentUtterance = utterance
    utterance.lang = locale
    utterance.rate = 0.95
    if (voice) utterance.voice = voice

    const completeChunk = () => {
      if (session !== playbackSession || currentUtterance !== utterance) return
      clearUtterance()
      chunkIndex += 1
      window.setTimeout(speakNext, 35)
    }
    utterance.onstart = () => {
      if (session !== playbackSession || currentUtterance !== utterance) return
      if (!playbackStarted) {
        playbackStarted = true
        callbacks.onSpeakingChange(true)
        startMouthAnimation(session)
      }
      lastBoundaryAt = performance.now()
      mouthPulse = 0.55
    }
    utterance.onboundary = () => {
      if (session !== playbackSession || currentUtterance !== utterance) return
      lastBoundaryAt = performance.now()
      mouthPulse = 0.55 + Math.random() * 0.4
    }
    utterance.onend = completeChunk
    utterance.onerror = completeChunk
    currentUtteranceTimeout = window.setTimeout(
      completeChunk,
      Math.min(20_000, Math.max(2_000, (chunk.length * 150) / utterance.rate)),
    )
    try {
      window.speechSynthesis.resume()
      window.speechSynthesis.speak(utterance)
    } catch {
      completeChunk()
    }
  }

  window.setTimeout(speakNext, 80)
}
