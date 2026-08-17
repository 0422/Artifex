import { Component, type ErrorInfo, type ReactNode } from 'react'
import { RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export default class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Application render failure', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div className="flex min-h-screen items-center justify-center bg-zinc-950 p-6 text-center">
        <div className="max-w-md">
          <h1 className="text-lg font-semibold text-zinc-100">页面显示出现异常</h1>
          <p className="mt-2 text-sm leading-6 text-zinc-500">浏览器翻译或扩展可能修改了页面结构。刷新后可继续使用。</p>
          <button onClick={() => window.location.reload()} className="primary-button mt-5"><RefreshCw size={16} />刷新页面</button>
        </div>
      </div>
    )
  }
}
