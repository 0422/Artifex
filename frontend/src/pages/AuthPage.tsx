import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AxiosError } from 'axios'
import { BarChart3, Cpu, Languages } from 'lucide-react'

import { authApi } from '../services/api'
// 2026-09-29 产品名改由 constants.ts 的 PRODUCT_NAME 统一提供
import { PRODUCT_NAME } from '../lib/constants'
import { useAuthStore } from '../stores/authStore'

/**
 * 2026-10-02 第三批：登录页品牌化重构。
 *
 * 原来是一张居中的 slate+indigo 小卡片——与应用主体的 zinc+teal 体系完全割裂
 * （用户对产品的第一印象就是这个页面），且输入框只有 placeholder 没有标签。
 * 现在改为「左品牌展示 + 右表单」双栏 Hero：
 *   · 左侧：A 字徽标（与 favicon 同一视觉语言）+ 产品主张 + 三个能力点
 *   · 右侧：表单卡片，输入框补标签，主按钮走 .primary-button
 */

const FEATURES = [
  { icon: Languages, title: '情境对话', desc: 'AI 扮演对话角色，边说边纠错' },
  { icon: BarChart3, title: '学情报告', desc: '每次练习产出评分与薄弱点分析' },
  { icon: Cpu, title: '边缘设备', desc: '局域网设备扫描、认领与 OTA 升级' },
]

/** 品牌徽标：teal 渐变圆角方 + 深色 A，与 public/favicon.svg 同一设计 */
function BrandMark({ size = 'h-9 w-9 text-[15px]' }: { size?: string }) {
  return (
    <span className={`flex ${size} shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-400 to-teal-600 font-bold text-teal-950`} aria-hidden>
      A
    </span>
  )
}

export default function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const resp =
        mode === 'login'
          ? await authApi.login(email, password)
          : await authApi.register(email, password, nickname || undefined)
      setAuth(resp.access_token, resp.user)
      navigate('/')
    } catch (err) {
      const ax = err as AxiosError<{ detail?: string }>
      setError(ax.response?.data?.detail ?? '操作失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      {/* 左栏：品牌展示。lg 以下隐藏——窄窗口直接进表单，不做拥堵的双栏 */}
      <div className="relative hidden overflow-hidden lg:block">
        {/* 右上往左下洒一层 teal 微光，给纯色底加点空间纵深 */}
        <div className="absolute inset-0 bg-[radial-gradient(75%_60%_at_25%_30%,rgba(45,212_191,0.13),transparent_70%)]" />
        <div className="relative flex h-full flex-col justify-between p-12">
          <div className="flex items-center gap-3">
            <BrandMark />
            <span className="text-lg font-semibold tracking-wide text-zinc-100">{PRODUCT_NAME}</span>
          </div>

          <div className="max-w-md">
            <h1 className="text-3xl font-semibold leading-snug text-zinc-100">
              和 AI 伙伴一起，
              <br />
              把语言练成本能
            </h1>
            <p className="mt-4 text-sm leading-6 text-zinc-400">情境对话、即时纠错、学情报告——练习的每一步都有反馈。</p>
            <ul className="mt-10 space-y-5">
              {FEATURES.map(({ icon: Icon, title, desc }) => (
                <li key={title} className="flex items-start gap-3.5">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900 text-teal-300">
                    <Icon size={17} />
                  </span>
                  <div>
                    <p className="text-sm font-medium text-zinc-200">{title}</p>
                    <p className="mt-0.5 text-xs leading-5 text-zinc-500">{desc}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <p className="text-xs text-zinc-600">{PRODUCT_NAME} · 全领域 AI 学习伙伴</p>
        </div>
      </div>

      {/* 右栏：表单 */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          {/* 窄窗口下左栏隐藏，徽标在这里补一个，避免页面光秃秃 */}
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <BrandMark size="h-8 w-8 text-sm" />
            <span className="font-semibold text-zinc-100">{PRODUCT_NAME}</span>
          </div>

          <h2 className="text-xl font-semibold text-zinc-100">{mode === 'login' ? '登录' : '注册'}</h2>
          <p className="mt-1.5 text-sm text-zinc-400">{mode === 'login' ? '继续你的练习进度' : '创建账号，开始第一次练习'}</p>

          <form onSubmit={submit} className="mt-8 space-y-5">
            {mode === 'register' && (
              <label className="block">
                <span className="mb-1.5 block text-xs font-medium text-zinc-400">昵称（可选）</span>
                <input
                  type="text"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  className="field"
                  placeholder="怎么称呼你"
                />
              </label>
            )}
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-zinc-400">邮箱</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="field"
                placeholder="you@example.com"
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-zinc-400">密码</span>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="field"
                placeholder={mode === 'register' ? '至少 8 位' : '请输入密码'}
              />
            </label>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <button type="submit" disabled={loading} className="primary-button h-10 w-full justify-center text-sm">
              {loading ? '处理中…' : mode === 'login' ? '登录' : '注册'}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-zinc-500">
            {mode === 'login' ? '还没有账号？' : '已有账号？'}
            <button
              type="button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="ml-1 text-teal-400 transition-colors hover:text-teal-300"
            >
              {mode === 'login' ? '注册一个' : '去登录'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
