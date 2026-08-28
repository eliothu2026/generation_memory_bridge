import { useEffect, useRef, useState } from 'react'
import type { SessionSnapshot } from '../../api/provider'
import Composer from './Composer'
import ElderBubble from './ElderBubble'
import GrandchildBubble from './GrandchildBubble'

interface Props {
  snap: SessionSnapshot
  elderName: string
  onNext: () => void
  onSend: (text: string) => void
}

export default function ChatArea({ snap, elderName, onNext, onSend }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const canAdvance = snap.segmentsPlayed < snap.totalSegments

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [snap.messages.length])

  const handleSend = () => {
    if (!input.trim()) return
    onSend(input)
    setInput('')
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
              <p className="mt-6 text-sm">点击下方「老人继续讲 ▶」,开始逐段聆听与整理。</p>
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
                onPickFollowUp={setInput}
              />
            ) : (
              <GrandchildBubble key={m.id} text={m.text} />
            ),
          )}
          <div ref={bottomRef} />
        </div>
      </div>
      <Composer value={input} onChange={setInput} onSend={handleSend} onNext={onNext} canAdvance={canAdvance} />
    </div>
  )
}
