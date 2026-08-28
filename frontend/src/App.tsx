import { useState } from 'react'
import type { Mode } from './api/provider'
import ChatArea from './components/Chat/ChatArea'
import Sidebar from './components/Sidebar/Sidebar'
import TimelinePanel from './components/Timeline/TimelinePanel'
import TopBar from './components/TopBar'
import { useSession } from './hooks/useSession'

export default function App() {
  const [mode, setMode] = useState<Mode>('offline')
  const { snap, loading, error, next, send, reset } = useSession(mode)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [timelineCollapsed, setTimelineCollapsed] = useState(false)

  const title = snap?.meta.title || '代际记忆桥梁'
  const elderName = snap?.meta.elder_name ?? '老人'

  return (
    <div className="flex h-full w-full overflow-hidden font-sans text-ink">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
        sessionTitle={title}
        sessionSubtitle={snap?.meta.subtitle}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          sessionTitle={title}
          segmentsPlayed={snap?.segmentsPlayed ?? 0}
          totalSegments={snap?.totalSegments ?? 0}
          onReset={reset}
          mode={mode}
          onModeChange={setMode}
        />

        {loading ? (
          <div className="flex flex-1 items-center justify-center text-subtle">加载中…</div>
        ) : error ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
            <div className="text-sm text-red-600">连接失败:{error}</div>
            <div className="max-w-md text-xs leading-relaxed text-subtle">
              {mode === 'backend'
                ? '「实时(后端)」需要先启动后端:pip install -e ".[web]" 后 uvicorn narrator_flow.server.app:app;或切回上方「离线演示」。'
                : '请先生成 demo 数据:python scripts/gen_demo_script.py'}
            </div>
          </div>
        ) : snap ? (
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
        ) : null}
      </div>
    </div>
  )
}
