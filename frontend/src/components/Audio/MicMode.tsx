import { useRef, useState } from 'react'
import type { SessionSnapshot } from '../../api/provider'
import ChatArea from '../Chat/ChatArea'
import TimelinePanel from '../Timeline/TimelinePanel'

type Phase = 'idle' | 'recording' | 'stopping' | 'done' | 'error'
const SEGMENT_MS = 4000 // 每 ~4 秒切一段完整录音发给后端

/**
 * 实时麦克风模式:浏览器采麦 → 每 ~4s 切出一段完整音频 → WS 二进制推给后端 →
 * faster-whisper 转写 → 背压合并队列 + worker → 真实分析,快照流式回推。
 *
 * MediaRecorder 的 timeslice 分片不可独立解码,故用「录一段→stop→拿完整 blob→再录下一段」。
 */
export default function MicMode({ onOpenSettings }: { onOpenSettings?: () => void }) {
  const [snap, setSnap] = useState<SessionSnapshot | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [timelineCollapsed, setTimelineCollapsed] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const recRef = useRef<MediaRecorder | null>(null)
  const recordingRef = useRef(false)

  const pickMime = (): string => {
    const cands = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg']
    for (const c of cands) {
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(c)) return c
    }
    return ''
  }

  const recordSegment = () => {
    const stream = streamRef.current
    if (!stream || !recordingRef.current) return
    const mime = pickMime()
    const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
    recRef.current = rec
    const chunks: BlobPart[] = []
    rec.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data)
    }
    rec.onstop = () => {
      const blob = new Blob(chunks, { type: mime || 'audio/webm' })
      const ws = wsRef.current
      if (blob.size > 0 && ws && ws.readyState === WebSocket.OPEN) ws.send(blob)
      if (recordingRef.current) recordSegment() // 立刻开始下一段
    }
    rec.start()
    setTimeout(() => {
      if (rec.state !== 'inactive') rec.stop()
    }, SEGMENT_MS)
  }

  const start = async () => {
    setError(null)
    setStatus('连接后端…')
    setSnap(null)
    try {
      const res = await fetch('/api/mic', { method: 'POST' })
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
      setStatus('请求麦克风权限…')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/ws/mic/${id}`)
      wsRef.current = ws
      ws.onmessage = (ev) => {
        const m = JSON.parse(ev.data as string)
        if (m.type === 'snapshot') setSnap(m.snapshot)
        else if (m.type === 'status') setStatus(m.message)
        else if (m.type === 'done') {
          setPhase('done')
          setStatus('已结束')
        } else if (m.type === 'error') setError(m.message)
      }
      ws.onerror = () => {
        setPhase('error')
        setError('WebSocket 连接失败(后端是否已启动?)')
      }
      ws.onopen = () => {
        recordingRef.current = true
        setPhase('recording')
        setStatus('正在聆听…请对着麦克风讲述')
        recordSegment()
      }
    } catch (e) {
      setPhase('error')
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const stop = () => {
    recordingRef.current = false
    setPhase('stopping')
    setStatus('处理最后片段…')
    if (recRef.current && recRef.current.state !== 'inactive') recRef.current.stop()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }))
  }

  if (!snap) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="flex w-full max-w-md flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-black/10 bg-surface px-6 py-12 text-center">
          <div className="text-4xl">🎤</div>
          <div className="text-sm font-medium text-ink">实时麦克风 · 边听边理解</div>
          <div className="text-xs leading-relaxed text-subtle">
            对着麦克风讲述,浏览器每 ~4 秒把一段音频送去转写 → 背压合并 → 真实分析。
            <br />
            需后端已启动、配 DEEPSEEK_API_KEY、装 <code className="rounded bg-slate-100 px-1">[asr]</code>,并允许麦克风权限。
          </div>
          {error && <div className="text-xs text-red-600">{error}</div>}
          <button onClick={start} className="mt-2 rounded-full bg-accent px-4 py-2 text-sm font-medium text-white">
            开始聆听
          </button>
          {onOpenSettings && (
            <button onClick={onOpenSettings} className="text-xs text-subtle underline-offset-2 hover:underline">
              ⚙️ 配置 API Key
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-2 border-b border-black/5 bg-surface px-6 py-2 text-xs">
        {phase === 'recording' && <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />}
        <span className={error ? 'text-red-600' : 'text-subtle'}>{error ? `出错:${error}` : status}</span>
        <div className="ml-auto">
          {phase === 'recording' ? (
            <button onClick={stop} className="rounded-full bg-red-500 px-3 py-1 text-xs font-medium text-white">
              ■ 停止聆听
            </button>
          ) : (
            <button onClick={start} className="rounded-full bg-accent px-3 py-1 text-xs font-medium text-white">
              重新开始
            </button>
          )}
        </div>
      </div>
      <div className="flex min-h-0 flex-1">
        <ChatArea
          snap={snap}
          elderName={snap.meta.elder_name ?? '长辈'}
          mode="audio"
          readOnly
          onNext={() => {}}
          onSend={() => {}}
        />
        <TimelinePanel
          timeline={snap.timeline}
          eraEstimate={snap.eraEstimate}
          collapsed={timelineCollapsed}
          onToggle={() => setTimelineCollapsed((v) => !v)}
          segmentsPlayed={snap.segmentsPlayed}
          totalSegments={snap.totalSegments}
        />
      </div>
    </div>
  )
}
