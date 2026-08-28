import { useRef, useState } from 'react'
import { Loader2, Mic, Paperclip, Send, Square } from 'lucide-react'

type InputMethod = 'text' | 'upload' | 'mic'
const SEGMENT_MS = 4000 // 麦克风每 ~4s 切一段完整录音

interface Props {
  busy: boolean
  onElder: (text: string) => void
  onGrandchild: (text: string) => void
  onAudio: (blob: Blob) => void
}

/**
 * 会话内统一输入器:文字(老人/我)/ 录音上传 / 实时麦克风。
 * 三者都通过同一条会话 WS 把"老人输入"送进后端(文字直发,音频发二进制帧)。
 */
export default function LiveComposer({ busy, onElder, onGrandchild, onAudio }: Props) {
  const [method, setMethod] = useState<InputMethod>('text')
  const [speaker, setSpeaker] = useState<'elder' | 'grandchild'>('elder')
  const [text, setText] = useState('')
  const [recording, setRecording] = useState(false)
  const streamRef = useRef<MediaStream | null>(null)
  const recRef = useRef<MediaRecorder | null>(null)
  const recordingRef = useRef(false)

  const submitText = () => {
    const t = text.trim()
    if (!t) return
    setText('')
    if (speaker === 'elder') onElder(t)
    else onGrandchild(t)
  }

  const pickMime = () => {
    for (const c of ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg']) {
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(c)) return c
    }
    return ''
  }
  const recordSeg = () => {
    const s = streamRef.current
    if (!s || !recordingRef.current) return
    const mime = pickMime()
    const rec = mime ? new MediaRecorder(s, { mimeType: mime }) : new MediaRecorder(s)
    recRef.current = rec
    const chunks: BlobPart[] = []
    rec.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data)
    }
    rec.onstop = () => {
      const b = new Blob(chunks, { type: mime || 'audio/webm' })
      if (b.size > 0) onAudio(b)
      if (recordingRef.current) recordSeg()
    }
    rec.start()
    setTimeout(() => {
      if (rec.state !== 'inactive') rec.stop()
    }, SEGMENT_MS)
  }
  const startMic = async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = s
      recordingRef.current = true
      setRecording(true)
      recordSeg()
    } catch {
      /* 用户拒绝麦克风权限 */
    }
  }
  const stopMic = () => {
    recordingRef.current = false
    setRecording(false)
    if (recRef.current && recRef.current.state !== 'inactive') recRef.current.stop()
    streamRef.current?.getTracks().forEach((t) => t.stop())
  }

  const seg = (active: boolean) =>
    'rounded-full px-2.5 py-1 transition ' + (active ? 'bg-white text-ink shadow-soft' : 'text-subtle hover:text-ink')
  const chip = (active: boolean, tone: 'amber' | 'blue') =>
    'rounded-full px-2.5 py-0.5 transition ' +
    (active ? (tone === 'amber' ? 'bg-amber-100 text-amber-900' : 'bg-blue-100 text-blue-900') : 'text-subtle')

  return (
    <div className="border-t border-black/5 bg-surface px-4 py-3 md:px-10">
      <div className="mx-auto max-w-3xl">
        <div className="mb-2 flex items-center gap-1.5 text-xs">
          <span className="text-subtle">输入方式:</span>
          <div className="flex items-center rounded-full bg-slate-100 p-0.5 font-medium">
            <button onClick={() => setMethod('text')} className={seg(method === 'text')}>💬 文字</button>
            <button onClick={() => setMethod('upload')} className={seg(method === 'upload')}>🎙️ 上传</button>
            <button onClick={() => setMethod('mic')} className={seg(method === 'mic')}>🎤 麦克风</button>
          </div>
          {busy && (
            <span className="flex items-center gap-1 text-subtle">
              <Loader2 size={12} className="animate-spin" /> 分析中…
            </span>
          )}
        </div>

        {method === 'text' && (
          <div className="flex items-center gap-2">
            <div className="flex flex-none items-center rounded-full border border-black/10 bg-white p-0.5 text-xs font-medium">
              <button onClick={() => setSpeaker('elder')} className={chip(speaker === 'elder', 'amber')}>👵 老人</button>
              <button onClick={() => setSpeaker('grandchild')} className={chip(speaker === 'grandchild', 'blue')}>🧑 我</button>
            </div>
            <div className="flex flex-1 items-center gap-2 rounded-full border border-black/10 bg-white px-4 py-2 shadow-soft focus-within:border-accent/40">
              <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
                    e.preventDefault()
                    submitText()
                  }
                }}
                placeholder={speaker === 'elder' ? '以长辈身份说一段往事…(真实模型分析)' : '替孙辈说点什么…'}
                className="min-w-0 flex-1 bg-transparent text-[15px] text-ink outline-none placeholder:text-subtle"
              />
              <button
                onClick={submitText}
                disabled={!text.trim()}
                className="flex h-8 w-8 flex-none items-center justify-center rounded-full text-accent transition enabled:hover:bg-accent/10 disabled:text-slate-300"
                title="发送"
              >
                <Send size={17} />
              </button>
            </div>
          </div>
        )}

        {method === 'upload' && (
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-full border-2 border-dashed border-black/10 bg-white px-4 py-3 text-sm text-subtle transition hover:border-accent/40">
            <Paperclip size={16} /> 选择音频文件(上传 → 转写 → 背压 → 分析)
            <input
              type="file"
              accept="audio/*,.wav,.mp3,.m4a,.aiff"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) onAudio(f)
              }}
            />
          </label>
        )}

        {method === 'mic' && (
          <div className="flex items-center justify-center gap-3 py-1">
            {!recording ? (
              <button onClick={startMic} className="flex items-center gap-2 rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-600">
                <Mic size={16} /> 开始聆听
              </button>
            ) : (
              <button onClick={stopMic} className="flex items-center gap-2 rounded-full bg-red-500 px-4 py-2 text-sm font-medium text-white">
                <Square size={13} /> 停止(每 ~4s 一段)
              </button>
            )}
            {recording && (
              <span className="flex items-center gap-1 text-xs text-subtle">
                <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" /> 正在聆听
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
