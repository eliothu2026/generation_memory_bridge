import { useState } from 'react'
import { OfflineProvider } from './api/offlineProvider'
import ChatArea from './components/Chat/ChatArea'
import Sidebar from './components/Sidebar/Sidebar'
import TimelinePanel from './components/Timeline/TimelinePanel'
import TopBar from './components/TopBar'
import { useSession } from './hooks/useSession'

export default function App() {
  const { snap, loading, error, next, send, reset } = useSession(() => new OfflineProvider())
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [timelineCollapsed, setTimelineCollapsed] = useState(false)

  if (loading) {
    return <div className="flex h-full items-center justify-center text-subtle">加载中…</div>
  }
  if (error || !snap) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-6 text-center text-sm text-red-600">
        加载失败:{error ?? '未知错误'}
        <span className="mt-2 block text-subtle">
          请先运行 <code className="rounded bg-slate-100 px-1">python scripts/gen_demo_script.py</code> 生成 demo 数据。
        </span>
      </div>
    )
  }

  const elderName = snap.meta.elder_name ?? '老人'

  return (
    <div className="flex h-full w-full overflow-hidden font-sans text-ink">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
        sessionTitle={snap.meta.title}
        sessionSubtitle={snap.meta.subtitle}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          sessionTitle={snap.meta.title}
          segmentsPlayed={snap.segmentsPlayed}
          totalSegments={snap.totalSegments}
          onReset={reset}
        />
        <div className="flex min-h-0 flex-1">
          <ChatArea snap={snap} elderName={elderName} onNext={next} onSend={send} />
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
    </div>
  )
}
