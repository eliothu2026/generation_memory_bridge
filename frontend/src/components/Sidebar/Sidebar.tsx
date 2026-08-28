import { Menu, MessageSquare, Plus } from 'lucide-react'
import SessionCard from './SessionCard'

interface Props {
  collapsed: boolean
  onToggle: () => void
  onNewSession: () => void
  sessionTitle: string
  sessionSubtitle?: string
}

// 演示占位卡:让侧栏看起来丰满,但明确标注为占位,不伪造数据。
const PLACEHOLDERS = [
  { title: '外公的旧收音机', subtitle: '演示占位 · 待录入' },
  { title: '奶奶的针线笸箩', subtitle: '演示占位 · 待录入' },
]

export default function Sidebar({ collapsed, onToggle, onNewSession, sessionTitle, sessionSubtitle }: Props) {
  if (collapsed) {
    return (
      <div className="flex w-16 flex-none flex-col items-center gap-4 bg-sidebar py-4">
        <button onClick={onToggle} className="rounded-full p-2 text-subtle hover:bg-black/5" title="展开侧栏">
          <Menu size={20} />
        </button>
        <button onClick={onNewSession} className="rounded-full bg-white p-2.5 text-accent shadow-soft" title="新建会话">
          <Plus size={18} />
        </button>
        <div className="rounded-full bg-white/70 p-2 text-accent" title={sessionTitle}>
          <MessageSquare size={18} />
        </div>
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
        <div className="px-2 pb-1 text-xs font-medium text-subtle">今天</div>
        <SessionCard title={sessionTitle} subtitle={sessionSubtitle} active />

        <div className="mt-4 px-2 pb-1 text-xs font-medium text-subtle">前 7 天</div>
        {PLACEHOLDERS.map((p) => (
          <SessionCard key={p.title} title={p.title} subtitle={p.subtitle} muted />
        ))}
      </div>

      <div className="px-5 py-3 text-[11px] leading-relaxed text-subtle">演示模式 · 免 key · 数据本地回放</div>
    </div>
  )
}
