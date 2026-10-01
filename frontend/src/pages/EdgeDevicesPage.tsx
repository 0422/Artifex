import { useEffect, useMemo, useState } from 'react'
import { Cpu, Loader2, Plus, Radar, Search } from 'lucide-react'

import { EDGE_CHIP_LABEL as CHIP_LABEL } from '../lib/constants'
import type { DiscoveredDevice, EdgeDevice, EdgeScanResult } from '../lib/types'
import { edgeDevicesApi } from '../services/api'
import EdgeDeviceDetail from '../components/EdgeDeviceDetail'

export default function EdgeDevicesPage() {
  const [devices, setDevices] = useState<EdgeDevice[]>([])
  const [scan, setScan] = useState<EdgeScanResult | null>(null)
  const [selected, setSelected] = useState<EdgeDevice | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState('')
  const [claiming, setClaiming] = useState<DiscoveredDevice | null>(null)

  const onlineIds = useMemo(
    () => new Set((scan?.matched ?? []).filter((item) => item.online).map((item) => item.device_id)),
    [scan],
  )

  const loadDevices = () =>
    edgeDevicesApi.list().then((data) => {
      setDevices(data)
      // 设备被删除后及时收起详情抽屉
      setSelected((current) => data.find((item) => item.id === current?.id) ?? null)
    })

  const runScan = async () => {
    setScanning(true)
    setError('')
    try {
      const result = await edgeDevicesApi.scan()
      setScan(result)
      // 扫描会更新设备在线状态，顺手刷新档案保持两边一致
      await loadDevices()
      return result
    } catch (err) {
      setError(err instanceof Error ? err.message : '扫描失败，请检查后端能否绑定 UDP 4210 端口')
      return undefined
    } finally {
      setScanning(false)
    }
  }

  // 2026-09-30 新增边缘设备管理模块：进入页面主动扫描一次，
  // 之后只在用户点「搜索设备」时重新扫描，不做轮询。
  // cancelled 标志避免组件卸载后仍 setState
  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        await Promise.all([loadDevices(), runScan()])
      } catch {
        // 失败提示已由 runScan 内部写入 error
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const claimDevice = (ip: string) => {
    const found = (scan?.unclaimed ?? []).find((item) => item.ip === ip)
    setClaiming(found ?? { ip, payload: '', seen_count: 0 })
  }

  const unclaimed = scan?.unclaimed ?? []

  return (
    <div className="flex h-full min-h-0 bg-zinc-900">
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-14 shrink-0 flex-wrap items-center gap-3 border-b border-zinc-800 px-4 py-2 sm:px-6">
          <div className="min-w-0 flex-1">
            {/* 2026-10-01 「边缘管理」更名为「边缘设备」，与侧边栏导航保持一致 */}
            <h1 className="truncate text-sm font-semibold text-zinc-100">边缘设备</h1>
            <p className="text-xs text-zinc-500">
              {scanning
                ? '正在扫描局域网...'
                : scan
                  ? `上次扫描 ${new Date(scan.scanned_at).toLocaleTimeString()} · 端口 ${scan.port} · ${scan.matched.filter((m) => m.online).length}/${devices.length} 在线 · ${unclaimed.length} 个未认领`
                  : loading
                    ? '正在加载...'
                    : '尚未扫描'}
            </p>
          </div>
          <button onClick={runScan} disabled={scanning} className="secondary-button">
            {scanning ? <Loader2 size={15} className="animate-spin" /> : <Radar size={15} />}
            {scanning ? '扫描中' : '搜索设备'}
          </button>
          <button onClick={() => setClaiming({ ip: '', payload: '', seen_count: 0 })} className="primary-button">
            <Plus size={15} />手动添加
          </button>
        </header>

        {error && (
          <p className="border-b border-red-900 bg-red-950/40 px-5 py-2 text-xs text-red-300">{error}</p>
        )}

        {unclaimed.length > 0 && (
          <div className="border-b border-zinc-800 bg-amber-950/20 px-4 py-3 sm:px-6">
            <h2 className="text-xs font-medium text-amber-300">
              发现 {unclaimed.length} 个未认领设备
            </h2>
            <p className="mt-1 text-xs text-zinc-500">
              固件只广播 IP 地址，不带名称与型号。认领后请手动补充设备信息。
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {unclaimed.map((item) => (
                <button
                  key={item.ip}
                  onClick={() => claimDevice(item.ip)}
                  className="flex items-center gap-2 rounded border border-zinc-700 bg-zinc-950 px-2.5 py-1.5 text-xs text-zinc-300 hover:border-teal-600 hover:text-teal-300"
                >
                  <Cpu size={13} />
                  {item.ip}
                  <span className="text-zinc-600">{item.seen_count} 次广播</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
          {!loading && devices.length === 0 && <EmptyState onAdd={() => setClaiming({ ip: '', payload: '', seen_count: 0 })} />}
          <div className="grid gap-3 sm:grid-cols-2 2xl:grid-cols-3">
            {devices.map((device) => (
              <DeviceCard
                key={device.id}
                device={device}
                // 扫描结果是本页最新鲜的在线状态，优先于档案里的旧值
                online={onlineIds.has(device.id)}
                selected={selected?.id === device.id}
                onClick={() => setSelected(device)}
              />
            ))}
          </div>
        </div>
      </section>

      <aside
        className={`${selected || claiming ? 'flex' : 'hidden'} fixed inset-y-0 right-0 z-40 w-full max-w-md flex-col border-l border-zinc-700 bg-zinc-950 shadow-2xl xl:static xl:z-auto xl:w-96 xl:shadow-none`}
      >
        {selected && (
          <EdgeDeviceDetail
            device={selected}
            onClose={() => setSelected(null)}
            onSaved={(updated) => {
              setSelected(updated)
              void loadDevices()
            }}
          />
        )}
        {claiming && !selected && (
          <ClaimForm
            initialIp={claiming.ip}
            onClose={() => setClaiming(null)}
            onSaved={async (device) => {
              setClaiming(null)
              await loadDevices()
              setSelected(device)
            }}
          />
        )}
      </aside>
    </div>
  )
}

function DeviceCard({
  device,
  online,
  selected,
  onClick,
}: {
  device: EdgeDevice
  online: boolean
  selected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`min-h-40 rounded-lg border p-4 text-left transition-colors ${selected ? 'border-teal-700 bg-teal-950/30' : 'border-zinc-800 bg-zinc-950/50 hover:border-zinc-700 hover:bg-zinc-900'}`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="rounded bg-zinc-800 px-2 py-1 text-[10px] text-zinc-400">
          {CHIP_LABEL[device.chip] ?? device.chip}
        </span>
        <span className="flex items-center gap-1.5 text-[10px]">
          <span className={`h-1.5 w-1.5 rounded-full ${online ? 'bg-teal-400' : 'bg-zinc-600'}`} />
          <span className={online ? 'text-teal-300' : 'text-zinc-500'}>{online ? '在线' : '离线'}</span>
        </span>
      </div>
      <h2 className="mt-4 font-medium text-zinc-100">{device.name}</h2>
      <p className="mt-2 font-mono text-xs text-zinc-500">{device.ip_address ?? '未设置 IP'}</p>
      <div className="mt-4 flex flex-wrap items-center gap-2 text-[10px] text-zinc-500">
        <span>固件 {device.firmware_version ?? '未知'}</span>
        {device.wifi_ssid && (
          <>
            <span>·</span>
            <span>WiFi {device.wifi_ssid}</span>
          </>
        )}
      </div>
    </button>
  )
}

function ClaimForm({
  initialIp,
  onClose,
  onSaved,
}: {
  initialIp: string
  onClose: () => void
  onSaved: (device: EdgeDevice) => void | Promise<void>
}) {
  const [name, setName] = useState('')
  const [chip, setChip] = useState('esp32s3')
  const [ip, setIp] = useState(initialIp)
  const [firmwareVersion, setFirmwareVersion] = useState('')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const save = async () => {
    if (!name.trim()) return
    setSaving(true)
    setError('')
    try {
      const device = await edgeDevicesApi.create({
        name: name.trim(),
        chip,
        ip_address: ip.trim() || null,
        firmware_version: firmwareVersion.trim() || null,
        notes: notes.trim() || null,
      })
      await onSaved(device)
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <header className="flex h-14 items-center justify-between border-b border-zinc-800 px-4">
        <span className="text-sm font-semibold">认领设备</span>
        <button onClick={onClose} title="关闭" className="icon-button">
          <Plus size={17} className="rotate-45" />
        </button>
      </header>
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
        <Field label="设备名称">
          <input
            autoFocus
            className="field mt-1.5"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="例如：书桌助手"
          />
        </Field>
        <Field label="芯片型号">
          <select className="field mt-1.5" value={chip} onChange={(event) => setChip(event.target.value)}>
            {Object.entries(CHIP_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="IP 地址">
          <input
            className="field mt-1.5 font-mono"
            value={ip}
            onChange={(event) => setIp(event.target.value)}
            placeholder="192.168.1.42"
          />
        </Field>
        <Field label="固件版本">
          <input
            className="field mt-1.5"
            value={firmwareVersion}
            onChange={(event) => setFirmwareVersion(event.target.value)}
            placeholder="例如：3.0.1"
          />
        </Field>
        <Field label="备注">
          <textarea
            className="field mt-1.5 min-h-20 resize-y"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </Field>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
      <footer className="flex justify-end gap-2 border-t border-zinc-800 p-4">
        <button onClick={onClose} className="secondary-button">
          取消
        </button>
        <button disabled={!name.trim() || saving} onClick={save} className="primary-button">
          {saving ? '保存中...' : '认领'}
        </button>
      </footer>
    </>
  )
}

function EmptyState({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="mx-auto max-w-sm py-24 text-center">
      <Search className="mx-auto text-zinc-700" size={34} />
      <h2 className="mt-4 font-medium text-zinc-300">还没有绑定任何设备</h2>
      <p className="mt-2 text-sm text-zinc-600">
        点「搜索设备」扫描局域网，或手动添加一台设备的 IP。
      </p>
      <button onClick={onAdd} className="primary-button mt-5">
        <Plus size={15} />
        手动添加设备
      </button>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm text-zinc-300">{label}{children}</label>
}
