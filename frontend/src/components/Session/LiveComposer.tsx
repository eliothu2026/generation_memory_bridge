import { useRef, useState } from 'react'
import { Mic, Paperclip, PenLine, Send, Square } from 'lucide-react'
import { toWav16k } from '../../lib/wav'

type Panel = 'none' | 'text' | 'upload'
const SEGMENT_MS = 4000 // 麦克风每 ~4s 切一段完整录音

interface Props {
  busy: boolean
  onElder: (text: string) => void
  onGrandchild: (text: string) => void
  onAudio: (blob: Blob) => void
}

/** 聆听态声波:五根竖条错峰起伏(与静态 demo 同款动画)。 */
function Wave() {
  return (
    <span className="flex h-5 items-center gap-[3px]">
      {[0, 1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className="block w-[3px] animate-wave rounded-[2px] bg-accent"
          style={{ height: 6, animationDelay: `${i * 0.18}s` }}
        />
      ))}
    </span>
  )
}

/**
 * 会话内统一输入器。
 * 「陪伴聆听」是一等入口:一个常驻主按钮,点一下就开始实时转写(每 ~4s 自动切段);
 * 文字 / 上传录音降为旁边的次入口,点开才展开——避免把「说话」藏进三选一里。
 */
export default function LiveComposer({ busy, onElder, onGrandchild, onAudio }: Props) {
  const [panel, setPanel] = useState<Panel>('none')
  const [speaker, setSpeaker] = useState<'elder' | 'grandchild'>('elder')
  const [text, setText] = useState('')
  const [recording, setRecording] = useState(false)
  const streamRef = useRef<MediaStream | null>(null)
  const recRef = useRef<MediaRecorder | null>(null)
  const recordingRef = useRef(false)

  const submitText = () => {
    const t = text.trim()
    if (!t || busy) return
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
    rec.onstop = async () => {
      const raw = new Blob(chunks, { type: mime || 'audio/webm' })
      if (raw.size > 0) {
        // 转 16k 单声道 WAV:云端 ASR(Step/OpenAI)普遍不收 webm;失败则原样兜底
        try {
          onAudio(await toWav16k(raw))
        } catch {
          onAudio(raw)
        }
      }
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
      setPanel('none')
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

  const secondary = (active: boolean) =>
    'flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs transition ' +
    (active ? 'bg-ink/10 text-ink' : 'text-subtle hover:bg-ink/5 hover:text-ink')
  const chip = (active: boolean, tone: 'elder' | 'me') =>
    'rounded-full px-2.5 py-0.5 transition ' +
    (active ? (tone === 'elder' ? 'bg-accent/15 text-accent' : 'bg-ink/10 text-ink') : 'text-subtle')

  return (
    <div className="bg-canvas px-6 pb-5 pt-2">
      <div className="mx-auto max-w-[720px]">
        {panel === 'text' && (
          <div className="mb-2 flex items-center gap-2">
            <div className="flex flex-none items-center rounded-full border border-ink/10 bg-elev p-0.5 text-xs font-medium">
              <button onClick={() => setSpeaker('elder')} className={chip(speaker === 'elder', 'elder')}>
                👵 老人
              </button>
              <button onClick={() => setSpeaker('grandchild')} className={chip(speaker === 'grandchild', 'me')}>
                🧑 我
              </button>
            </div>
            <div className="flex flex-1 items-center gap-2 rounded-full border border-ink/10 bg-elev px-4 py-2 shadow-soft focus-within:border-accent/40">
              <input
                autoFocus
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
                disabled={!text.trim() || busy}
                className="flex h-8 w-8 flex-none items-center justify-center rounded-full text-accent transition enabled:hover:bg-accent/10 disabled:text-faint"
                title="发送"
              >
                <Send size={17} />
              </button>
            </div>
          </div>
        )}

        {panel === 'upload' && (
          <label className="mb-2 flex cursor-pointer items-center justify-center gap-2 rounded-full border-2 border-dashed border-ink/10 bg-elev px-4 py-3 text-sm text-subtle transition hover:border-accent/40">
            <Paperclip size={16} /> 选择一段录音(上传 → 转写 → 自动整理)
            <input
              type="file"
              accept="audio/*,.wav,.mp3,.m4a,.aiff"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) {
                  onAudio(f)
                  setPanel('none')
                }
              }}
            />
          </label>
        )}

        <div className="flex items-center justify-center gap-2">
          {/* 一等入口:陪伴聆听 */}
          <button
            onClick={recording ? stopMic : startMic}
            className={
              'flex items-center gap-2.5 rounded-full py-1.5 pl-1.5 pr-4 transition ' +
              (recording
                ? 'bg-accent/10 text-accent'
                : 'bg-accent-fill text-on-accent shadow-soft hover:bg-accent-strong')
            }
            title={recording ? '结束陪伴聆听' : '开启 AI 陪伴聆听'}
          >
            <span className="relative flex h-9 w-9 flex-none items-center justify-center rounded-full bg-white/15">
              {recording && <span className="absolute inset-0 animate-ping rounded-full border-2 border-accent" />}
              {recording ? <Square size={13} /> : <Mic size={17} />}
            </span>
            <span className="text-left">
              <span className="block text-[13px] font-semibold leading-tight">
                {recording ? '正在聆听这场对话' : '开启 AI 陪伴聆听'}
              </span>
              <span
                className={
                  'block text-[11px] leading-tight ' + (recording ? 'text-faint' : 'text-on-accent/70')
                }
              >
                {recording ? '点击结束 · 每 ~4s 自动切一段' : '点一下开始,老人直接说就行'}
              </span>
            </span>
            {recording && <Wave />}
          </button>

          {/* 次入口:文字 / 上传录音 */}
          {!recording && (
            <>
              <button
                onClick={() => setPanel(panel === 'text' ? 'none' : 'text')}
                className={secondary(panel === 'text')}
              >
                <PenLine size={14} /> 文字
              </button>
              <button
                onClick={() => setPanel(panel === 'upload' ? 'none' : 'upload')}
                className={secondary(panel === 'upload')}
              >
                <Paperclip size={14} /> 上传录音
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
