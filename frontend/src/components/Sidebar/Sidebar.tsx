import { Menu, MessageSquare, Plus, Sparkles, Trash2 } from 'lucide-react'
import type { SessionSummary } from '../../api/sessionApi'

interface Props {
  collapsed: boolean
  onToggle: () => void
  sessions: SessionSummary[]
  activeId: string | null // null => 离线示例
  backendError: string | null
  onSelectOffline: () => void
  onSelectSession: (id: string) => void
  onNewSession: () => void
  onDeleteSession: (id: string) => void
}

export default function Sidebar({
  collapsed,
  onToggle,
  sessions,
  activeId,
  backendError,
  onSelectOffline,
  onSelectSession,
  onNewSession,
  onDeleteSession,
}: Props) {
  if (collapsed) {
    return (
      <div className="flex w-16 flex-none flex-col items-center gap-4 bg-sidebar py-4">
        <button onClick={onToggle} className="rounded-full p-2 text-subtle hover:bg-black/5" title="展开侧栏">
          <Menu size={20} />
        </button>
        <button onClick={onNewSession} className="rounded-full bg-white p-2.5 text-accent shadow-soft" title="新建会话">
          <Plus size={18} />
        </button>
        <button onClick={onSelectOffline} className="rounded-full bg-white/70 p-2 text-accent" title="离线示例">
          <Sparkles size={18} />
        </button>
      </div>
    )
  }
  return (
    <div className="flex w-72 flex-none flex-col bg-sidebar">
      <div className="flex items-center gap-2 px-4 py-4">
        <button onClick={onToggle} className="rounded-full p-2 text-subtle hover:bg-black/5" title="收起侧栏">
          <Menu size={20} />
        </button>
        <div className="text-[15px] font-semibold text-ink">代际记忆桥梁</div>
      </div>

      <div className="px-3">
        <button
          onClick={onNewSession}
          className="flex w-full items-center gap-2 rounded-full bg-white px-4 py-2.5 text-sm font-medium text-ink shadow-soft transition hover:shadow-panel"
        >
          <Plus size={18} className="text-accent" /> 新建会话
        </button>
      </div>

      <div className="mt-4 min-h-0 flex-1 overflow-y-auto px-3">
        {/* 置顶:离线示例(免 key、免后端) */}
        <div className="px-2 pb-1 text-xs font-medium text-subtle">示例</div>
        <div
          onClick={onSelectOffline}
          className={
            'mb-3 flex cursor-pointer items-start gap-2.5 rounded-xl px-3 py-2.5 transition ' +
            (activeId === null ? 'bg-white shadow-soft' : 'hover:bg-black/5')
          }
        >
          <Sparkles size={16} className={'mt-0.5 flex-none ' + (activeId === null ? 'text-accent' : 'text-subtle')} />
          <div className="min-w-0">
            <div className="truncate text-sm font-medium text-ink">大槐树的故事</div>
            <div className="truncate text-xs text-subtle">离线回放 · 免 key</div>
          </div>
        </div>

        <div className="px-2 pb-1 text-xs font-medium text-subtle">我的会话</div>
        {backendError && (
          <div className="mb-2 rounded-lg bg-amber-50 px-3 py-2 text-[11px] leading-relaxed text-amber-800">
            后端未连接,无法管理真实会话。请启动 <code>uvicorn narrator_flow.server.app:app</code>。
          </div>
        )}
        {!backendError && sessions.length === 0 && (
          <div className="px-3 py-2 text-xs text-subtle">还没有会话,点上方「新建会话」开始。</div>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            onClick={() => onSelectSession(s.id)}
            className={
              'group mb-1 flex cursor-pointer items-center gap-2.5 rounded-xl px-3 py-2.5 transition ' +
              (activeId === s.id ? 'bg-white shadow-soft' : 'hover:bg-black/5')
            }
          >
            <MessageSquare size={16} className={'flex-none ' + (activeId === s.id ? 'text-accent' : 'text-subtle')} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-ink">{s.title}</div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDeleteSession(s.id)
              }}
              className="flex-none rounded-full p-1 text-subtle opacity-0 transition hover:bg-black/10 hover:text-red-600 group-hover:opacity-100"
              title="删除会话"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <div className="px-5 py-3 text-[11px] leading-relaxed text-subtle">会话持久化于后端 SQLite</div>
    </div>
  )
}
