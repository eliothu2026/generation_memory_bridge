import { useCallback, useEffect, useState } from 'react'
import { createSession, deleteSession, listSessions, type SessionSummary } from './api/sessionApi'
import LiveSessionView from './components/Session/LiveSessionView'
import OfflineView from './components/Session/OfflineView'
import SettingsModal from './components/SettingsModal'
import Sidebar from './components/Sidebar/Sidebar'
import TopBar from './components/TopBar'

export default function App() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null) // null => 离线示例
  const [backendError, setBackendError] = useState<string | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [timelineCollapsed, setTimelineCollapsed] = useState(false)

  const refresh = useCallback(async () => {
    try {
      setSessions(await listSessions())
      setBackendError(null)
    } catch {
      setBackendError('后端未连接')
    }
  }, [])
  useEffect(() => {
    refresh()
  }, [refresh])

  const newSession = async () => {
    try {
      const id = await createSession()
      await refresh()
      setActiveId(id)
    } catch {
      setBackendError('后端未连接')
      setSettingsOpen(true) // 多半是后端没起 / 未配置,顺手打开配置
    }
  }

  const removeSession = async (id: string) => {
    try {
      await deleteSession(id)
      if (activeId === id) setActiveId(null)
      await refresh()
    } catch {
      setBackendError('后端未连接')
    }
  }

  const title = activeId ? sessions.find((s) => s.id === activeId)?.title || '会话' : '大槐树的故事'
  const subtitle = activeId ? '实时(后端)· 真实分析' : '离线演示 · 免 key'

  return (
    <div className="flex h-full w-full overflow-hidden font-sans text-ink">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
        sessions={sessions}
        activeId={activeId}
        backendError={backendError}
        onSelectOffline={() => setActiveId(null)}
        onSelectSession={setActiveId}
        onNewSession={newSession}
        onDeleteSession={removeSession}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar title={title} subtitle={subtitle} onOpenSettings={() => setSettingsOpen(true)} />
        {activeId ? (
          <LiveSessionView
            key={activeId}
            id={activeId}
            timelineCollapsed={timelineCollapsed}
            onToggleTimeline={() => setTimelineCollapsed((v) => !v)}
          />
        ) : (
          <OfflineView
            timelineCollapsed={timelineCollapsed}
            onToggleTimeline={() => setTimelineCollapsed((v) => !v)}
          />
        )}
      </div>

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={() => {
          setSettingsOpen(false)
          refresh()
        }}
      />
    </div>
  )
}
