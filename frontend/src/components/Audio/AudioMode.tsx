import { useRef, useState } from 'react'
import type { SessionSnapshot } from '../../api/provider'
import ChatArea from '../Chat/ChatArea'
import TimelinePanel from '../Timeline/TimelinePanel'

type Phase = 'idle' | 'working' | 'done' | 'error'

/**
 * 音频模式:上传录音 → 后端 faster-whisper 转写 → 背压合并队列 + worker → 真实分析。
 * 与交互式会话不同,这里是**服务端推送**:上传后开一条 WS,被动接收流式快照。
 */
export default function AudioMode({ onOpenSettings }: { onOpenSettings?: () => void }) {
  const [snap, setSnap] = useState<SessionSnapshot | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [timelineCollapsed, setTimelineCollapsed] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const start = async (file: File) => {
    setPhase('working')
    setError(null)
    setStatus('上传中…')
    setSnap(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch('/api/audio', { method: 'POST', body: fd })
      if (!res.ok) {
        let detail = `HTTP ${res.status}`
        try {
          const j = await res.json()
          if (j.detail) detail = j.detail
        } catch {
          /* ignore */
        }
        throw new Error(detail)
      }
      const { id, snapshot } = await res.json()
      setSnap(snapshot)
      setStatus('已上传,连接分析中…')

      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/ws/audio/${id}`)
      wsRef.current = ws
      ws.onmessage = (ev) => {
        const m = JSON.parse(ev.data as string)
        if (m.type === 'snapshot') setSnap(m.snapshot)
        else if (m.type === 'status') setStatus(m.message)
        else if (m.type === 'done') {
          setPhase('done')
          setStatus('分析完成')
        } else if (m.type === 'error') {
          setPhase('error')
          setError(m.message)
        }
      }
      ws.onerror = () => {
        setPhase('error')
        setError('WebSocket 连接失败(后端是否已启动?)')
      }
    } catch (e) {
      setPhase('error')
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  if (phase === 'idle') {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
        <label className="flex w-full max-w-md cursor-pointer flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-black/10 bg-surface px-6 py-12 text-center transition hover:border-accent/40">
          <div className="text-4xl">🎙️</div>
          <div className="text-sm font-medium text-ink">上传一段长辈口述录音</div>
          <div className="text-xs leading-relaxed text-subtle">
            faster-whisper 转写 → 背压合并队列 → 真实分析
            <br />
            需后端已启动、配 DEEPSEEK_API_KEY,且 <code className="rounded bg-slate-100 px-1">pip install -e ".[asr]"</code>
          </div>
          <span className="mt-2 rounded-full bg-accent px-4 py-2 text-sm font-medium text-white">选择音频文件</span>
          <input
            type="file"
            accept="audio/*,.wav,.mp3,.m4a,.aiff"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) start(f)
            }}
          />
        </label>
        {onOpenSettings && (
          <button onClick={onOpenSettings} className="text-xs text-subtle underline-offset-2 hover:underline">
            ⚙️ 配置 API Key
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-2 border-b border-black/5 bg-surface px-6 py-2 text-xs">
        {phase === 'working' && <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />}
        <span className={phase === 'error' ? 'text-red-600' : 'text-subtle'}>
          {phase === 'error' ? `出错:${error}` : phase === 'done' ? '✅ 分析完成' : status || '处理中…'}
        </span>
      </div>
      <div className="flex min-h-0 flex-1">
        {snap && (
          <ChatArea
            snap={snap}
            elderName={snap.meta.elder_name ?? '长辈'}
            mode="audio"
            readOnly
            onNext={() => {}}
            onSend={() => {}}
          />
        )}
        {snap && (
          <TimelinePanel
            timeline={snap.timeline}
            eraEstimate={snap.eraEstimate}
            collapsed={timelineCollapsed}
            onToggle={() => setTimelineCollapsed((v) => !v)}
            segmentsPlayed={snap.segmentsPlayed}
            totalSegments={snap.totalSegments}
          />
        )}
      </div>
    </div>
  )
}
