import { useEffect, useState } from 'react'
import { X } from 'lucide-react'

interface Props {
  open: boolean
  onClose: () => void
  onSaved: () => void
}

/**
 * 模型配置弹窗:热配置 DeepSeek 的 API Key / Base URL(POST /api/config)。
 * key 只存于后端进程内存、不落盘;保存后触发 onSaved(通常用于重连当前会话)。
 */
export default function SettingsModal({ open, onClose, onSaved }: Props) {
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setMsg(null)
    setApiKey('')
    fetch('/api/config')
      .then((r) => r.json())
      .then((d) => {
        setConfigured(d.configured)
        setBaseUrl(d.base_url || '')
      })
      .catch(() => setConfigured(null))
  }, [open])

  if (!open) return null

  const save = async () => {
    setSaving(true)
    setMsg(null)
    try {
      const body: Record<string, string> = {}
      if (apiKey.trim()) body.api_key = apiKey.trim()
      if (baseUrl.trim()) body.base_url = baseUrl.trim()
      const r = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}(后端是否已启动?)`)
      const d = await r.json()
      setConfigured(d.configured)
      setMsg('已保存,正在重连…')
      onSaved()
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-2xl bg-white p-5 shadow-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold text-ink">模型配置 · DeepSeek</div>
          <button onClick={onClose} className="rounded-full p-1 text-subtle hover:bg-slate-100" title="关闭">
            <X size={16} />
          </button>
        </div>
        <div className="mb-3 text-xs leading-relaxed text-subtle">
          {configured === null
            ? '⚠️ 未连接后端(请先启动 uvicorn)'
            : configured
              ? '● 已配置 API Key(可在此更改)'
              : '○ 尚未配置 API Key'}
          <br />
          key 仅保存在后端进程内存中,不写入磁盘。
        </div>

        <label className="mb-1 block text-xs font-medium text-ink">API Key</label>
        <input
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          type="password"
          placeholder="sk-…(留空表示不修改)"
          className="mb-3 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-accent/40"
        />

        <label className="mb-1 block text-xs font-medium text-ink">Base URL(可选)</label>
        <input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://api.deepseek.com"
          className="mb-4 w-full rounded-lg border border-black/10 px-3 py-2 text-sm outline-none focus:border-accent/40"
        />

        <div className="flex items-center justify-between gap-3">
          <span className="min-w-0 flex-1 truncate text-xs text-subtle">{msg}</span>
          <button
            onClick={save}
            disabled={saving}
            className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-600 disabled:opacity-60"
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
