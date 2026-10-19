import { useEffect, useState } from 'react'
import { X } from 'lucide-react'

interface Props {
  open: boolean
  onClose: () => void
  onSaved: () => void
}

/**
 * 模型配置弹窗:热配置 LLM(DeepSeek)与 ASR。
 * ASR 两档:本地 faster-whisper(离线免 key) / 云端 OpenAI 兼容接口(StepFun、OpenAI…)。
 * 全部只写进后端进程内存、不落盘;保存后触发 onSaved(通常用于重连当前会话)。
 */
const LOCAL_MODELS = ['tiny', 'base', 'small', 'medium', 'large-v3']
const CLOUD_MODELS = ['stepaudio-3-asr-max', 'stepaudio-2.5-asr', 'stepaudio-2-asr-pro', 'whisper-1']
const STEP_BASE = 'https://api.stepfun.com/v1'
const OPENAI_BASE = 'https://api.openai.com/v1'

const inputCls =
  'w-full rounded-[10px] border border-ink/10 bg-elev px-3 py-2 text-sm outline-none focus:border-accent/40'

export default function SettingsModal({ open, onClose, onSaved }: Props) {
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [asrProvider, setAsrProvider] = useState<'local' | 'cloud'>('local')
  const [asrModel, setAsrModel] = useState('')
  const [asrBaseUrl, setAsrBaseUrl] = useState('')
  const [asrKey, setAsrKey] = useState('')
  const [asrHasKey, setAsrHasKey] = useState(false)
  const [asrAvailable, setAsrAvailable] = useState<boolean | null>(null)
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setMsg(null)
    setApiKey('')
    setAsrKey('')
    fetch('/api/config')
      .then((r) => r.json())
      .then((d) => {
        setConfigured(d.configured)
        setBaseUrl(d.base_url || '')
        setAsrProvider(d.asr_provider === 'cloud' ? 'cloud' : 'local')
        setAsrModel(d.asr_model || '')
        setAsrBaseUrl(d.asr_base_url || STEP_BASE)
        setAsrHasKey(!!d.asr_has_key)
        setAsrAvailable(d.asr_available ?? null)
      })
      .catch(() => setConfigured(null))
  }, [open])

  if (!open) return null

  const switchProvider = (p: 'local' | 'cloud') => {
    setAsrProvider(p)
    if (p === 'cloud') {
      setAsrBaseUrl(asrBaseUrl || STEP_BASE)
      if (!asrModel || LOCAL_MODELS.includes(asrModel)) setAsrModel('stepaudio-3-asr-max')
    } else if (!asrModel || !LOCAL_MODELS.includes(asrModel)) {
      setAsrModel('small')
    }
  }

  const save = async () => {
    setSaving(true)
    setMsg(null)
    try {
      const body: Record<string, string> = {}
      if (apiKey.trim()) body.api_key = apiKey.trim()
      if (baseUrl.trim()) body.base_url = baseUrl.trim()
      body.asr_provider = asrProvider
      body.asr_model = asrModel.trim()
      // 清空即回落到各自默认(本地 small / 云端 stepaudio-3-asr-max)
      body.asr_base_url = asrProvider === 'cloud' ? asrBaseUrl.trim() : ''
      if (asrKey.trim()) body.asr_api_key = asrKey.trim()
      const r = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}(后端是否已启动?)`)
      const d = await r.json()
      setConfigured(d.configured)
      setAsrProvider(d.asr_provider === 'cloud' ? 'cloud' : 'local')
      setAsrModel(d.asr_model || '')
      setAsrBaseUrl(d.asr_base_url || STEP_BASE)
      setAsrHasKey(!!d.asr_has_key)
      setMsg('已保存,正在重连…')
      onSaved()
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const seg = (active: boolean) =>
    'flex-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition ' +
    (active ? 'bg-elev text-ink shadow-soft' : 'text-subtle hover:text-ink')

  const chip = (active: boolean) =>
    'rounded-full px-2.5 py-1 text-[11px] font-medium transition ' +
    (active ? 'bg-accent/15 text-accent' : 'bg-ink/5 text-subtle hover:text-ink')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4" onClick={onClose}>
      <div
        className="max-h-[92vh] w-full max-w-md overflow-y-auto rounded-card bg-surface p-5 shadow-float"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold text-ink">模型配置</div>
          <button onClick={onClose} className="rounded-full p-1 text-subtle hover:bg-ink/5" title="关闭">
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
          className={inputCls + ' mb-3'}
        />

        <label className="mb-1 block text-xs font-medium text-ink">Base URL(可选)</label>
        <input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="https://api.deepseek.com"
          className={inputCls + ' mb-3'}
        />

        <label className="mb-1 flex items-center justify-between text-xs font-medium text-ink">
          <span>语音识别 · ASR</span>
          <span className="text-[11px] font-normal text-faint">
            {asrProvider === 'local' ? '本地 · 离线免 key' : '云端 · 按量计费'}
          </span>
        </label>
        <div className="mb-2 flex rounded-full bg-ink/5 p-0.5">
          <button onClick={() => switchProvider('local')} className={seg(asrProvider === 'local')}>
            本地 faster-whisper
          </button>
          <button onClick={() => switchProvider('cloud')} className={seg(asrProvider === 'cloud')}>
            云端 API(Step / OpenAI)
          </button>
        </div>

        {asrProvider === 'local' ? (
          <>
            <input
              value={asrModel}
              onChange={(e) => setAsrModel(e.target.value)}
              placeholder="small(留空则用默认)"
              className={inputCls}
            />
            <div className="mt-2 flex flex-wrap gap-1.5">
              {LOCAL_MODELS.map((m) => (
                <button key={m} onClick={() => setAsrModel(m)} className={chip(asrModel === m)}>
                  {m}
                </button>
              ))}
            </div>
            <div className="mb-4 mt-2 text-[11px] leading-relaxed text-faint">
              模型越大越准、也越慢(默认 small),首次使用需联网下载;国内网络可先
              <code className="mx-0.5 rounded bg-ink/5 px-1">export HF_ENDPOINT=https://hf-mirror.com</code>
              再启动后端。也可直接填任意 HuggingFace 模型 id。
              {asrAvailable === false && (
                <span className="mt-1 block text-danger">
                  ⚠️ 后端未安装 faster-whisper,转写会失败:
                  <code className="mx-0.5 rounded bg-ink/5 px-1">pip install -e ".[asr]"</code>
                </span>
              )}
            </div>
          </>
        ) : (
          <>
            <div className="mb-2 flex items-center gap-2">
              <input
                value={asrBaseUrl}
                onChange={(e) => setAsrBaseUrl(e.target.value)}
                placeholder={STEP_BASE}
                className={inputCls}
              />
            </div>
            <div className="mb-2 flex flex-wrap gap-1.5">
              <button
                onClick={() => {
                  setAsrBaseUrl(STEP_BASE)
                  setAsrModel('stepaudio-3-asr-max')
                }}
                className={chip(asrBaseUrl.includes('stepfun'))}
              >
                阶跃 StepFun
              </button>
              <button
                onClick={() => {
                  setAsrBaseUrl(OPENAI_BASE)
                  setAsrModel('whisper-1')
                }}
                className={chip(asrBaseUrl.includes('openai'))}
              >
                OpenAI
              </button>
            </div>

            <label className="mb-1 block text-xs font-medium text-ink">ASR API Key</label>
            <input
              value={asrKey}
              onChange={(e) => setAsrKey(e.target.value)}
              type="password"
              placeholder={asrHasKey ? '● 已配置(留空不修改)' : '填写该 ASR 服务的 API Key'}
              className={inputCls + ' mb-2'}
            />

            <label className="mb-1 block text-xs font-medium text-ink">ASR 模型</label>
            <input
              value={asrModel}
              onChange={(e) => setAsrModel(e.target.value)}
              placeholder="stepaudio-3-asr-max"
              className={inputCls}
            />
            <div className="mt-2 flex flex-wrap gap-1.5">
              {CLOUD_MODELS.map((m) => (
                <button key={m} onClick={() => setAsrModel(m)} className={chip(asrModel === m)}>
                  {m}
                </button>
              ))}
            </div>
            <div className="mb-4 mt-2 text-[11px] leading-relaxed text-faint">
              Step 走 <code className="rounded bg-ink/5 px-1">/audio/asr/sse</code>(StepAudio 3),
              其他服务走 OpenAI 兼容的 <code className="rounded bg-ink/5 px-1">/audio/transcriptions</code>,
              按域名自动判别。麦克风录音会先转成 16kHz WAV 再上传(Step 不收 webm)。
            </div>
          </>
        )}

        <div className="flex items-center justify-between gap-3">
          <span className="min-w-0 flex-1 truncate text-xs text-subtle">{msg}</span>
          <button
            onClick={save}
            disabled={saving}
            className="rounded-full bg-accent-fill px-4 py-2 text-sm font-medium text-on-accent transition hover:bg-accent-strong disabled:opacity-60"
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
