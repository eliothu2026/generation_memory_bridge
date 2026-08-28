import ChatArea from '../Chat/ChatArea'
import TimelinePanel from '../Timeline/TimelinePanel'
import { useSession } from '../../hooks/useSession'

interface Props {
  timelineCollapsed: boolean
  onToggleTimeline: () => void
}

/** 离线示例「大槐树」:本地回放,免 key、免后端。逐段「老人继续讲」推进脚本。 */
export default function OfflineView({ timelineCollapsed, onToggleTimeline }: Props) {
  const { snap, loading, error, next, send } = useSession('offline')

  if (loading || !snap) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-subtle">
        {error ? `加载失败:${error}(先运行 python scripts/gen_demo_script.py)` : '加载中…'}
      </div>
    )
  }
  return (
    <div className="flex min-h-0 flex-1">
      <ChatArea snap={snap} elderName={snap.meta.elder_name ?? '老人'} mode="offline" onNext={next} onSend={send} />
      <TimelinePanel
        timeline={snap.timeline}
        eraEstimate={snap.eraEstimate}
        collapsed={timelineCollapsed}
        onToggle={onToggleTimeline}
        segmentsPlayed={snap.segmentsPlayed}
        totalSegments={snap.totalSegments}
      />
    </div>
  )
}
