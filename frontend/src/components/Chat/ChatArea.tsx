import { useEffect, useRef, useState } from 'react'
import type { Mode, SessionSnapshot } from '../../api/provider'
import Composer from './Composer'
import ElderBubble from './ElderBubble'
import GrandchildBubble from './GrandchildBubble'

interface Props {
  snap: SessionSnapshot
  elderName: string
  mode: Mode
  onNext: () => Promise<void> | void
  onSend: (text: string) => Promise<void> | void
  onSubmitElder?: (text: string) => Promise<void> | void
  readOnly?: boolean
}

export default function ChatArea({ snap, elderName, mode, onNext, onSend, onSubmitElder, readOnly }: Props) {
  const [input, setInput] = useState('')
  const [speaker, setSpeaker] = useState<'elder' | 'grandchild'>('elder')
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const backend = mode === 'backend'
  const canAdvance = snap.segmentsPlayed < snap.totalSegments

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [snap.messages.length, busy])

  const doSend = async () => {
    const t = input.trim()
    if (!t || busy) return
    setInput('')
    if (backend && speaker === 'elder' && onSubmitElder) {
      setBusy(true)
      try {
        await onSubmitElder(t)
      } finally {
        setBusy(false)
      }
    } else {
      await onSend(t)
    }
  }

  const doNext = async () => {
    if (busy) return
    setBusy(true)
    try {
      await onNext()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col bg-surface">
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-10">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {snap.messages.length === 0 && (
            <div className="mt-24 text-center text-subtle">
              <div className="text-5xl">🌳</div>
              <p className="mt-4 text-lg font-medium text-ink">{snap.meta.title}</p>
              {snap.meta.subtitle && <p className="mt-1 text-sm">{snap.meta.subtitle}</p>}
              {!readOnly && (
                <p className="mt-6 text-sm">
                  {backend
                    ? '以「老人」身份输入一段口述,AI 会用真实模型实时整理(每段约 1–2 分钟)。'
                    : '点击下方「老人继续讲 ▶」,开始逐段聆听与整理。'}
                </p>
              )}
            </div>
          )}

          {snap.messages.map((m) =>
            m.speaker === 'elder' ? (
              <ElderBubble
                key={m.id}
                text={m.text}
                elderName={elderName}
                backgroundNotes={m.backgroundNotes}
                followUps={m.followUps}
                coalescedFrom={m.coalescedFrom}
                onPickFollowUp={readOnly ? () => {} : setInput}
              />
            ) : (
              <GrandchildBubble key={m.id} text={m.text} />
            ),
          )}

          {busy && backend && (
            <div className="flex animate-fade-in items-center gap-2 text-sm text-subtle">
              <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
              AI 正在分析这段口述…(真实模型,约 1–2 分钟)
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {!readOnly && (
        <Composer
          value={input}
          onChange={setInput}
          onSend={doSend}
          onNext={doNext}
          canAdvance={canAdvance}
          busy={busy}
          mode={mode}
          speaker={speaker}
          onSpeakerChange={setSpeaker}
        />
      )}
    </div>
  )
}
