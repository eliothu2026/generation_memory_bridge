import { useEffect, useRef, useState } from 'react'
import { useLiveSession } from '../../hooks/useLiveSession'
import ElderBubble from '../Chat/ElderBubble'
import GrandchildBubble from '../Chat/GrandchildBubble'
import ThinkingBubble from '../Chat/ThinkingBubble'
import TimelinePanel from '../Timeline/TimelinePanel'
import LiveComposer from './LiveComposer'

interface Props {
  id: string
  timelineCollapsed: boolean
  onToggleTimeline: () => void
}

/** 一条持久化会话的实时视图:服务端推送快照,渲染气泡 + 时间线 + 统一输入器。 */
export default function LiveSessionView({ id, timelineCollapsed, onToggleTimeline }: Props) {
  const { snap, error, notice, sendElderText, sendGrandchild, sendAudio } = useLiveSession(id)
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const elderCount = snap ? snap.messages.filter((m) => m.speaker === 'elder').length : 0
  const prevElder = useRef(elderCount)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [snap?.messages.length, busy])
  useEffect(() => {
    if (elderCount > prevElder.current) {
      setBusy(false)
      prevElder.current = elderCount
    }
  }, [elderCount])
  useEffect(() => {
    if (error) setBusy(false)
  }, [error])

  const onElder = (t: string) => {
    setBusy(true)
    sendElderText(t)
  }
  const onAudio = (b: Blob) => {
    setBusy(true)
    sendAudio(b)
  }

  if (!snap) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-subtle">
        {error ? `连接失败:${error}` : '连接会话中…'}
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {(notice || error) && (
        <div className="bg-canvas px-6 py-2 text-xs">
          <span className={error ? 'text-danger' : 'text-subtle'}>{error ? `⚠️ ${error}` : notice}</span>
        </div>
      )}
      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col bg-canvas">
          <div className="flex-1 overflow-y-auto px-6 py-4 lg:px-2">
            <div className="mx-auto flex max-w-[720px] flex-col gap-6">
              {snap.messages.length === 0 && (
                <div className="mt-24 text-center text-subtle">
                  <div className="text-5xl">🌱</div>
                  <p className="mt-4 text-sm leading-relaxed">
                    以「老人」身份说一段往事,或用 🎙️上传 / 🎤麦克风 输入语音,
                    <br />
                    AI 会实时整理出时间线、补背景、想追问。
                  </p>
                </div>
              )}
              {snap.messages.map((m) =>
                m.speaker === 'elder' ? (
                  <ElderBubble
                    key={m.id}
                    text={m.text}
                    elderName={snap.meta.elder_name ?? '长辈'}
                    backgroundNotes={m.backgroundNotes}
                    followUps={m.followUps}
                    coalescedFrom={m.coalescedFrom}
                    onPickFollowUp={() => {}}
                  />
                ) : (
                  <GrandchildBubble key={m.id} text={m.text} />
                ),
              )}
              {busy && <ThinkingBubble hint="真实模型分析,约 1–2 分钟" />}
              <div ref={bottomRef} />
            </div>
          </div>
          <LiveComposer busy={busy} onElder={onElder} onGrandchild={sendGrandchild} onAudio={onAudio} />
        </div>
        <TimelinePanel
          timeline={snap.timeline}
          eraEstimate={snap.eraEstimate}
          collapsed={timelineCollapsed}
          onToggle={onToggleTimeline}
          segmentsPlayed={snap.segmentsPlayed}
          totalSegments={snap.totalSegments}
        />
      </div>
    </div>
  )
}
