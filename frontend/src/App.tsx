import { useState } from 'react'
import { resolveMode, type LiveInput, type TopMode } from './api/provider'
import AudioMode from './components/Audio/AudioMode'
import ChatArea from './components/Chat/ChatArea'
import Sidebar from './components/Sidebar/Sidebar'
import TimelinePanel from './components/Timeline/TimelinePanel'
import TopBar from './components/TopBar'
import { useSession } from './hooks/useSession'

export default function App() {
  // 两级模式:顶层 演示/实时(平级);实时之下再分 文字模拟/真实语音
  const [topMode, setTopMode] = useState<TopMode>('demo')
  const [liveInput, setLiveInput] = useState<LiveInput>('text')
  const mode = resolveMode(topMode, liveInput) // 'offline' | 'backend' | 'audio'

  const { snap, loading, error, next, send, submitElder, reset } = useSession(mode)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [timelineCollapsed, setTimelineCollapsed] = useState(false)

  const title = mode === 'audio' ? '录音口述 · 实时分析' : snap?.meta.title || '代际记忆桥梁'
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
          topMode={topMode}
          liveInput={liveInput}
          onTopModeChange={setTopMode}
          onLiveInputChange={setLiveInput}
        />

        {mode === 'audio' ? (
          <AudioMode />
        ) : loading ? (
          <div className="flex flex-1 items-center justify-center text-subtle">
            {mode === 'backend' ? '连接后端中…' : '加载中…'}
          </div>
        ) : error ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 text-center">
            <div className="text-sm text-red-600">连接失败:{error}</div>
            <div className="max-w-md text-xs leading-relaxed text-subtle">
              {mode === 'backend'
                ? '「实时(后端)」需要先启动后端并配置 key:export DEEPSEEK_API_KEY=sk-... 后 uvicorn narrator_flow.server.app:app;或切回「演示模式」。'
                : '请先生成 demo 数据:python scripts/gen_demo_script.py'}
            </div>
          </div>
        ) : snap ? (
          <div className="flex min-h-0 flex-1">
            <ChatArea
              snap={snap}
              elderName={elderName}
              mode={mode}
              onNext={next}
              onSend={send}
              onSubmitElder={submitElder}
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
        ) : null}
      </div>
    </div>
  )
}
