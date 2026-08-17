import type { ChatServerEvent, ScenarioDifficulty } from '../lib/types'

type EventListener = (event: ChatServerEvent) => void
type StateListener = (state: 'connecting' | 'open' | 'closed') => void

export class ChatSocket {
  private socket: WebSocket | null = null
  private token: string | null = null
  private reconnectTimer: number | null = null
  private reconnectAttempts = 0
  private intentionallyClosed = false
  private readonly onEvent: EventListener
  private readonly onState: StateListener

  constructor(
    onEvent: EventListener,
    onState: StateListener,
  ) {
    this.onEvent = onEvent
    this.onState = onState
  }

  connect(token: string): void {
    this.disconnectSocket()
    this.token = token
    this.intentionallyClosed = false
    this.openSocket(token)
  }

  private openSocket(token: string): void {
    this.onState('connecting')
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/chat/ws`)
    this.socket = socket
    socket.onopen = () => {
      if (this.socket !== socket) return
      this.reconnectAttempts = 0
      this.onState('open')
      this.send({ type: 'authenticate', token })
    }
    socket.onmessage = (message) => {
      if (this.socket !== socket) return
      try {
        this.onEvent(JSON.parse(message.data) as ChatServerEvent)
      } catch {
        this.onEvent({ type: 'error', code: 'invalid_server_event', message: '服务返回了无法识别的消息', recoverable: true })
      }
    }
    socket.onerror = () => {
      if (this.socket !== socket) return
      this.onEvent({ type: 'error', code: 'connection_error', message: '无法连接到对话服务', recoverable: true })
    }
    socket.onclose = () => {
      if (this.socket !== socket) return
      this.socket = null
      this.onState('closed')
      if (!this.intentionallyClosed && this.token) this.scheduleReconnect()
    }
  }

  startSession(scenarioId: string, difficulty?: ScenarioDifficulty): void {
    this.send({ type: 'start_session', scenario_id: scenarioId, difficulty })
  }

  sendText(content: string): void {
    this.send({ type: 'text_message', content })
  }

  endSession(): void {
    this.send({ type: 'end_session' })
  }

  close(): void {
    this.intentionallyClosed = true
    this.token = null
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer)
    this.reconnectTimer = null
    this.disconnectSocket()
  }

  private disconnectSocket(): void {
    if (!this.socket) return
    this.socket.onopen = null
    this.socket.onmessage = null
    this.socket.onerror = null
    this.socket.onclose = null
    this.socket.close()
    this.socket = null
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) return
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 10_000)
    this.reconnectAttempts += 1
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      if (!this.intentionallyClosed && this.token) this.openSocket(this.token)
    }, delay)
  }

  private send(payload: object): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload))
    }
  }
}
