import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, Trash2, Upload, X } from 'lucide-react'
import * as Tabs from '@radix-ui/react-tabs'

import { EDGE_CHIP_LABEL as CHIP_LABEL } from '../lib/constants'
import type { EdgeDevice, EdgeFirmware, EdgeLlmInput, EdgeOtaTask } from '../lib/types'
import { EDGE_DEVICE_CHIPS } from '../lib/types'
import { edgeDevicesApi } from '../services/api'

const OTA_STATUS_LABEL: Record<EdgeOtaTask['status'], string> = {
  pending: '等待中',
  running: '推送中',
  success: '已完成',
  failed: '失败',
  canceled: '已取消',
}

const OTA_STATUS_CLASS: Record<EdgeOtaTask['status'], string> = {
  pending: 'text-zinc-400',
  running: 'text-teal-300',
  success: 'text-emerald-400',
  failed: 'text-red-400',
  canceled: 'text-zinc-500',
}

/** 设备端错误码 -> 中文提示。固件侧接口未实现时用户看到的是可操作的说明，不是裸错误 */
const ERROR_HINT: Record<string, string> = {
  'device-ota-unsupported': '设备固件暂不支持 OTA 升级，请改用有线烧录，或先升级设备端固件。',
  'device-api-unsupported': '设备固件暂不支持远程配置下发，请在 AP 配网模式（192.168.4.1）下手动设置。',
  'device-unreachable': '连不上设备，请确认它与本机在同一局域网且 IP 正确。',
  'device-timeout': '设备响应超时，请稍后重试。',
  'device-rejected': '设备拒绝了该请求，请查看任务日志中的原始返回。',
  'ip-not-allowed': '设备 IP 不在局域网范围内，已拒绝连接。',
  'invalid-ip': '设备 IP 格式不正确。',
}

function describeError(detail: unknown): string {
  if (typeof detail !== 'string') return '操作失败'
  const [code, ...rest] = detail.split(':')
  const hint = ERROR_HINT[code.trim()]
  const tail = rest.join(':').trim()
  return hint ? (tail && !hint.includes(tail) ? `${hint}（${tail}）` : hint) : detail
}

export default function EdgeDeviceDetail({
  device,
  onClose,
  onSaved,
}: {
  device: EdgeDevice
  onClose: () => void
  onSaved: (device: EdgeDevice) => void
}) {
  const [tab, setTab] = useState('profile')

  return (
    <>
      <header className="flex h-14 items-center justify-between border-b border-zinc-800 px-4">
        <div className="min-w-0">
          <span className="block truncate text-sm font-semibold">{device.name}</span>
          <span className="block truncate font-mono text-[10px] text-zinc-500">
            {device.ip_address ?? '未设置 IP'}
          </span>
        </div>
        <button onClick={onClose} title="关闭" className="icon-button">
          <X size={17} />
        </button>
      </header>

      <Tabs.Root value={tab} onValueChange={setTab} className="flex min-h-0 flex-1 flex-col">
        <Tabs.List className="flex shrink-0 gap-1 border-b border-zinc-800 px-3 py-2 text-xs">
          {[
            ['profile', '档案'],
            ['wifi', 'WiFi'],
            ['llm', 'LLM API'],
            ['prompt', 'Prompt'],
            ['ota', 'OTA'],
          ].map(([value, label]) => (
            <Tabs.Trigger
              key={value}
              value={value}
              className="rounded px-2.5 py-1.5 text-zinc-400 transition-colors hover:text-zinc-100 data-[state=active]:bg-teal-950 data-[state=active]:text-teal-300"
            >
              {label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {/* 用 key 绑定 device.id：切换设备时整棵子树重建，表单自然回到初始值，
            不必在 effect 里同步 state（那会触发额外渲染） */}
        <ProfileTab key={device.id} device={device} onSaved={onSaved} />
        <WifiTab key={device.id} device={device} onSaved={onSaved} />
        <LlmTab key={device.id} device={device} onSaved={onSaved} />
        <PromptTab key={device.id} device={device} onSaved={onSaved} />
        <OtaTab key={device.id} device={device} />
      </Tabs.Root>
    </>
  )
}

/** 统一的「下发」结果反馈条 */
function Feedback({ error, success }: { error: string; success: string }) {
  if (error) {
    return (
      <p className="rounded border border-red-900 bg-red-950/40 px-3 py-2 text-xs text-red-300">{error}</p>
    )
  }
  if (success) {
    return (
      <p className="rounded border border-emerald-900 bg-emerald-950/40 px-3 py-2 text-xs text-emerald-300">
        {success}
      </p>
    )
  }
  return null
}

function usePush() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const run = async (action: () => Promise<unknown>) => {
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      await action()
      setSuccess('已下发到设备')
      return true
    } catch (err) {
      setError(describeError(extractDetail(err)))
      return false
    } finally {
      setBusy(false)
    }
  }
  return { busy, error, success, setError, setSuccess, run }
}

/** axios 错误体在 response.data.detail，其余情况退回 message */
function extractDetail(err: unknown): unknown {
  const response = (err as { response?: { data?: { detail?: unknown } } })?.response
  if (response?.data?.detail !== undefined) return response.data.detail
  return (err as { message?: string })?.message
}

// ---------------------------------------------------------------------------
// 档案
// ---------------------------------------------------------------------------

function ProfileTab({
  device,
  onSaved,
}: {
  device: EdgeDevice
  onSaved: (device: EdgeDevice) => void
}) {
  const [form, setForm] = useState({
    name: device.name,
    chip: device.chip,
    ip_address: device.ip_address ?? '',
    mac_address: device.mac_address ?? '',
    firmware_version: device.firmware_version ?? '',
    notes: device.notes ?? '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const save = async () => {
    if (!form.name.trim()) return
    setSaving(true)
    setError('')
    try {
      const updated = await edgeDevicesApi.update(device.id, {
        name: form.name.trim(),
        chip: form.chip,
        ip_address: form.ip_address.trim() || null,
        mac_address: form.mac_address.trim() || null,
        firmware_version: form.firmware_version.trim() || null,
        notes: form.notes.trim() || null,
      })
      onSaved(updated)
    } catch (err) {
      setError(describeError(extractDetail(err)))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Tabs.Content value="profile" className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
      <Field label="设备名称">
        <input
          className="field mt-1.5"
          value={form.name}
          onChange={(event) => setForm({ ...form, name: event.target.value })}
        />
      </Field>
      <Field label="芯片型号">
        <select
          className="field mt-1.5"
          value={form.chip}
          onChange={(event) => setForm({ ...form, chip: event.target.value })}
        >
          {EDGE_DEVICE_CHIPS.map((chip) => (
            <option key={chip} value={chip}>
              {CHIP_LABEL[chip] ?? chip}
            </option>
          ))}
        </select>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="IP 地址">
          <input
            className="field mt-1.5 font-mono"
            value={form.ip_address}
            onChange={(event) => setForm({ ...form, ip_address: event.target.value })}
            placeholder="192.168.1.42"
          />
        </Field>
        <Field label="MAC 地址">
          <input
            className="field mt-1.5 font-mono"
            value={form.mac_address}
            onChange={(event) => setForm({ ...form, mac_address: event.target.value })}
            placeholder="AA:BB:CC:DD:EE:FF"
          />
        </Field>
      </div>
      <Field label="固件版本">
        <input
          className="field mt-1.5"
          value={form.firmware_version}
          onChange={(event) => setForm({ ...form, firmware_version: event.target.value })}
        />
      </Field>
      <Field label="备注">
        <textarea
          className="field mt-1.5 min-h-20 resize-y"
          value={form.notes}
          onChange={(event) => setForm({ ...form, notes: event.target.value })}
        />
      </Field>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <dl className="divide-y divide-zinc-800 border-y border-zinc-800 text-xs">
        <Row label="最近在线" value={device.last_online_at ? new Date(device.last_online_at).toLocaleString() : '从未'} />
        <Row label="创建时间" value={new Date(device.created_at).toLocaleString()} />
      </dl>
      <div className="flex justify-end">
        <button disabled={saving || !form.name.trim()} onClick={save} className="primary-button">
          {saving && <Loader2 size={14} className="animate-spin" />}
          {saving ? '保存中...' : '保存档案'}
        </button>
      </div>
    </Tabs.Content>
  )
}

// ---------------------------------------------------------------------------
// WiFi
// ---------------------------------------------------------------------------

function WifiTab({ device, onSaved }: { device: EdgeDevice; onSaved: (device: EdgeDevice) => void }) {
  const [ssid, setSsid] = useState('')
  const [password, setPassword] = useState('')
  const { busy, error, success, run } = usePush()

  return (
    <Tabs.Content value="wifi" className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
      <p className="rounded border border-amber-900/60 bg-amber-950/30 px-3 py-2 text-xs leading-5 text-amber-200/90">
        设备固件当前只在 AP 配网模式（连上 <span className="font-mono">Desk-Emoji</span> 热点后访问
        <span className="font-mono"> 192.168.4.1</span>）下写入 WiFi 凭证，STA 模式下暂不支持远程改密。
        此处下发在固件补齐管理接口后即可生效。
      </p>
      {device.wifi_ssid && (
        <p className="text-xs text-zinc-500">
          档案记录的网络：<span className="text-zinc-300">{device.wifi_ssid}</span>
        </p>
      )}
      <Field label="WiFi 名称（SSID）">
        <input
          className="field mt-1.5"
          value={ssid}
          onChange={(event) => setSsid(event.target.value)}
          placeholder="例如：HomeNet"
        />
      </Field>
      <Field label="WiFi 密码">
        <input
          type="password"
          className="field mt-1.5"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="留空表示开放网络"
        />
      </Field>
      <Feedback error={error} success={success} />
      <div className="flex justify-end">
        <button
          disabled={busy || !ssid.trim() || !device.ip_address}
          onClick={() =>
            run(async () => {
              const updated = await edgeDevicesApi.pushWifi(device.id, {
                ssid: ssid.trim(),
                password,
              })
              onSaved(updated)
            })
          }
          className="primary-button"
        >
          {busy && <Loader2 size={14} className="animate-spin" />}
          {busy ? '下发中...' : '下发 WiFi'}
        </button>
      </div>
    </Tabs.Content>
  )
}

// ---------------------------------------------------------------------------
// LLM API
// ---------------------------------------------------------------------------

function LlmTab({ device, onSaved }: { device: EdgeDevice; onSaved: (device: EdgeDevice) => void }) {
  const current = device.llm_config
  const [baseUrl, setBaseUrl] = useState(current?.base_url ?? '')
  const [model, setModel] = useState(current?.model ?? '')
  const [apiKey, setApiKey] = useState('')
  const [temperature, setTemperature] = useState(
    current?.temperature != null ? String(current.temperature) : '',
  )
  const { busy, error, success, run } = usePush()

  const submit = () =>
    run(async () => {
      const input: EdgeLlmInput = {
        base_url: baseUrl.trim() || null,
        model: model.trim() || null,
        temperature: temperature.trim() === '' ? null : Number(temperature),
      }
      // 留空 = 不改动已保存的 key；后端对 **** 开头的值同样按「未修改」处理
      if (apiKey.trim()) input.api_key = apiKey.trim()
      const updated = await edgeDevicesApi.pushLlmConfig(device.id, input)
      onSaved(updated)
      setApiKey('')
    })

  return (
    <Tabs.Content value="llm" className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
      <Field label="API Base URL">
        <input
          className="field mt-1.5 font-mono"
          value={baseUrl}
          onChange={(event) => setBaseUrl(event.target.value)}
          placeholder="https://api.example.com/v1"
        />
      </Field>
      <Field label="模型">
        <input
          className="field mt-1.5"
          value={model}
          onChange={(event) => setModel(event.target.value)}
          placeholder="例如：gpt-4o / deepseek-chat"
        />
      </Field>
      <Field label="API Key">
        <input
          type="password"
          className="field mt-1.5 font-mono"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          placeholder={current?.api_key ? `已保存（${current.api_key}），留空则不变` : 'sk-...'}
        />
      </Field>
      <p className="text-[11px] leading-5 text-zinc-600">
        密钥只在接口返回时脱敏显示（仅末 4 位）。留空表示沿用设备上已保存的值。
      </p>
      <Field label="Temperature">
        <input
          type="number"
          min="0"
          max="2"
          step="0.1"
          className="field mt-1.5"
          value={temperature}
          onChange={(event) => setTemperature(event.target.value)}
          placeholder="0 ~ 2"
        />
      </Field>
      <Feedback error={error} success={success} />
      <div className="flex justify-end">
        <button disabled={busy || !device.ip_address} onClick={submit} className="primary-button">
          {busy && <Loader2 size={14} className="animate-spin" />}
          {busy ? '下发中...' : '下发配置'}
        </button>
      </div>
    </Tabs.Content>
  )
}

// ---------------------------------------------------------------------------
// Prompt
// ---------------------------------------------------------------------------

function PromptTab({ device, onSaved }: { device: EdgeDevice; onSaved: (device: EdgeDevice) => void }) {
  const [prompt, setPrompt] = useState(device.prompt_config?.system_prompt ?? '')
  const { busy, error, success, setSuccess, run } = usePush()

  const restoreDefault = async () => {
    try {
      const { system_prompt } = await edgeDevicesApi.defaultPrompt()
      setPrompt(system_prompt)
      setSuccess('已填入默认模板，点「下发」写人设备')
    } catch {
      setSuccess('')
    }
  }

  return (
    <Tabs.Content value="prompt" className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-500">设备端默认系统 Prompt</span>
        <button onClick={restoreDefault} className="secondary-button h-8 text-xs">
          恢复默认模板
        </button>
      </div>
      <textarea
        className="field min-h-56 resize-y font-mono text-xs leading-6"
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        placeholder="定义设备的角色与回复风格"
      />
      <Feedback error={error} success={success} />
      <div className="flex justify-end">
        <button
          disabled={busy || !prompt.trim() || !device.ip_address}
          onClick={() =>
            run(async () => {
              const updated = await edgeDevicesApi.pushPrompt(device.id, {
                system_prompt: prompt.trim(),
              })
              onSaved(updated)
            })
          }
          className="primary-button"
        >
          {busy && <Loader2 size={14} className="animate-spin" />}
          {busy ? '下发中...' : '下发 Prompt'}
        </button>
      </div>
    </Tabs.Content>
  )
}

// ---------------------------------------------------------------------------
// OTA
// ---------------------------------------------------------------------------

function OtaTab({ device }: { device: EdgeDevice }) {
  const [firmware, setFirmware] = useState<EdgeFirmware[]>([])
  const [tasks, setTasks] = useState<EdgeOtaTask[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [version, setVersion] = useState('')
  const [chip, setChip] = useState(device.chip)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  const load = useCallback(() =>
    Promise.all([edgeDevicesApi.firmwareList(), edgeDevicesApi.otaTasks(device.id)])
      .then(([firmwareList, taskList]) => {
        setFirmware(firmwareList)
        setTasks(taskList)
      })
      .catch(() => setError('固件或任务列表加载失败')),
    [device.id],
  )

  useEffect(() => {
    void load()
  }, [load])

  // 有任务在跑时轮询详情，把分片进度显示出来；跑完自动停下
  useEffect(() => {
    const running = tasks.some((task) => task.status === 'running' || task.status === 'pending')
    if (!running) return
    const timer = window.setTimeout(() => void load(), 1500)
    return () => window.clearTimeout(timer)
  }, [tasks, load])

  const upload = async () => {
    if (!file || !version.trim()) return
    setUploading(true)
    setError('')
    try {
      await edgeDevicesApi.uploadFirmware(file, version.trim(), chip)
      setFile(null)
      setVersion('')
      if (fileInput.current) fileInput.current.value = ''
      await load()
    } catch (err) {
      setError(describeError(extractDetail(err)))
    } finally {
      setUploading(false)
    }
  }

  const push = async (firmwareId: string) => {
    setError('')
    try {
      await edgeDevicesApi.createOtaTask(device.id, firmwareId)
      await load()
    } catch (err) {
      setError(describeError(extractDetail(err)))
    }
  }

  const cancel = async (taskId: string) => {
    await edgeDevicesApi.cancelOtaTask(taskId).catch(() => undefined)
    await load()
  }

  return (
    <Tabs.Content value="ota" className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5">
      <section className="space-y-3">
        <h3 className="text-xs font-medium text-zinc-400">上传固件</h3>
        <div className="grid grid-cols-2 gap-3">
          <Field label="版本号">
            <input
              className="field mt-1.5"
              value={version}
              onChange={(event) => setVersion(event.target.value)}
              placeholder="例如：3.0.2"
            />
          </Field>
          <Field label="适用芯片">
            <select
              className="field mt-1.5"
              value={chip}
              onChange={(event) => setChip(event.target.value)}
            >
              {EDGE_DEVICE_CHIPS.map((item) => (
                <option key={item} value={item}>
                  {CHIP_LABEL[item] ?? item}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <input
          ref={fileInput}
          type="file"
          accept=".bin,.img,.elf"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="block w-full text-xs text-zinc-400 file:mr-3 file:rounded file:border-0 file:bg-zinc-800 file:px-3 file:py-1.5 file:text-xs file:text-zinc-200 hover:file:bg-zinc-700"
        />
        <button
          disabled={uploading || !file || !version.trim()}
          onClick={upload}
          className="primary-button"
        >
          {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          {uploading ? '上传中...' : '上传到固件仓库'}
        </button>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </section>

      <section className="space-y-2">
        <h3 className="text-xs font-medium text-zinc-400">固件仓库（{firmware.length}）</h3>
        {firmware.length === 0 && (
          <p className="text-xs text-zinc-600">还没有固件，先上传一个 .bin / .img 文件。</p>
        )}
        {firmware.map((item) => (
          <div
            key={item.id}
            className="flex items-center gap-3 rounded border border-zinc-800 bg-zinc-900/60 px-3 py-2"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs text-zinc-200">
                {item.version} · {CHIP_LABEL[item.chip] ?? item.chip}
              </p>
              <p className="truncate font-mono text-[10px] text-zinc-600">
                {item.filename} · {(item.size_bytes / 1024).toFixed(0)} KB · {item.sha256.slice(0, 12)}
              </p>
            </div>
            <button
              onClick={() => push(item.id)}
              disabled={!device.ip_address}
              title={device.ip_address ? '推送到本设备' : '设备未设置 IP'}
              className="secondary-button h-8 text-xs"
            >
              推送
            </button>
            <button
              onClick={() => edgeDevicesApi.deleteFirmware(item.id).then(load)}
              title="删除固件"
              className="icon-button"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </section>

      <section className="space-y-2">
        <h3 className="text-xs font-medium text-zinc-400">升级记录（{tasks.length}）</h3>
        {tasks.length === 0 && <p className="text-xs text-zinc-600">暂无升级记录。</p>}
        {tasks.map((task) => (
          <div key={task.id} className="rounded border border-zinc-800 bg-zinc-900/60 px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-xs text-zinc-300">
                {task.firmware ? `${task.firmware.version}` : '已删除的固件'}
              </span>
              <span className={`text-[11px] ${OTA_STATUS_CLASS[task.status]}`}>
                {OTA_STATUS_LABEL[task.status]}
              </span>
            </div>
            {(task.status === 'running' || task.status === 'pending') && (
              <div className="mt-2 h-1 overflow-hidden rounded bg-zinc-800">
                <div className="h-full bg-teal-500 transition-all" style={{ width: `${task.progress}%` }} />
              </div>
            )}
            {task.error && <p className="mt-1.5 text-[11px] leading-5 text-red-400">{describeError(task.error)}</p>}
            {task.log && (
              <pre className="mt-1.5 max-h-24 overflow-y-auto whitespace-pre-wrap font-mono text-[10px] leading-4 text-zinc-600">
                {task.log}
              </pre>
            )}
            {(task.status === 'running' || task.status === 'pending') && (
              <button onClick={() => cancel(task.id)} className="secondary-button mt-2 h-7 text-[11px]">
                取消
              </button>
            )}
          </div>
        ))}
      </section>
    </Tabs.Content>
  )
}

// ---------------------------------------------------------------------------
// 小部件
// ---------------------------------------------------------------------------

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm text-zinc-300">{label}{children}</label>
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 py-2.5">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="text-right text-zinc-300">{value}</dd>
    </div>
  )
}
