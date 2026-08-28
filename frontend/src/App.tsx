import { useState } from 'react'
import { resolveMode, type LiveInput, type TopMode } from './api/provider'
import AudioMode from './components/Audio/AudioMode'
import MicMode from './components/Audio/MicMode'
import ChatArea from './components/Chat/ChatArea'
import SettingsModal from './components/SettingsModal'
import Sidebar from './components/Sidebar/Sidebar'
import TimelinePanel from './components/Timeline/TimelinePanel'
import TopBar from './components/TopBar'
import { useSession } from './hooks/useSession'

export default function App() {
  // 两级模式:顶层 演示/实时(平级);实时之下再分 文字模拟/录音上传/实时麦克风
  const [topMode, setTopMode] = useState<TopMode>('demo')
  const [liveInput, setLiveInput] = useState<LiveInput>('text')
  const mode = resolveMode(topMode, liveInput) // 'offline' | 'backend' | 'audio' | 'mic'

  // 每次「新建会话」或保存配置后自增,触发当前模式重新初始化 / 组件重挂载
  const [sessionKey, setSessionKey] = useState(0)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [timelineCollapsed, setTimelineCollapsed] = useState(false)

  const { snap, loading, error, next, send, submitElder, reset } = useSession(mode, sessionKey)

  const newSession = () => setSessionKey((k) => k + 1)
  const openSettings = () => setSettingsOpen(true)

  const title =
    mode === 'mic'
      ? '实时麦克风 · 边听边理解'
      : mode === 'audio'
        ? '录音口述 · 实时分析'
        : snap?.meta.title || '代际记忆桥梁'
  const elderName = snap?.meta.elder_name ?? '老人'

  return (
    <div className="flex h-full w-full overflow-hidden font-sans text-ink">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
        onNewSession={newSession}
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
          onOpenSettings={openSettings}
        />

        {mode === 'audio' ? (
          <AudioMode key={sessionKey} onOpenSettings={openSettings} />
        ) : mode === 'mic' ? (
          <MicMode key={sessionKey} onOpenSettings={openSettings} />
        ) : loading ? (
          <div className="flex flex-1 items-center justify-center text-subtle">
            {mode === 'backend' ? '连接后端中…' : '加载中…'}
          </div>
        ) : error ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
            <div className="text-sm text-red-600">连接失败:{error}</div>
            {mode === 'backend' ? (
              <>
                <div className="max-w-md text-xs leading-relaxed text-subtle">
                  「实时(后端)」需先启动后端:<code className="rounded bg-slate-100 px-1">uvicorn narrator_flow.server.app:app</code>,
                  并配置 API Key(可点下方按钮,无需重启后端)。
                </div>
                <button
                  onClick={openSettings}
                  className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-600"
                >
                  配置 API Key
                </button>
              </>
            ) : (
              <div className="max-w-md text-xs leading-relaxed text-subtle">
                请先生成 demo 数据:python scripts/gen_demo_script.py
              </div>
            )}
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

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={() => {
          setSettingsOpen(false)
          newSession() // 配置生效后重连当前会话
        }}
      />
    </div>
  )
}
