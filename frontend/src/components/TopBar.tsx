import { RotateCcw } from 'lucide-react'
import type { Mode } from '../api/provider'

interface Props {
  sessionTitle: string
  segmentsPlayed: number
  totalSegments: number
  onReset: () => void
  mode: Mode
  onModeChange: (m: Mode) => void
}

export default function TopBar({
  sessionTitle,
  segmentsPlayed,
  totalSegments,
  onReset,
  mode,
  onModeChange,
}: Props) {
  const seg = (active: boolean) =>
    'rounded-full px-3 py-1 transition ' +
    (active ? 'bg-accent text-white shadow-soft' : 'text-subtle hover:text-ink')

  return (
    <header className="flex items-center justify-between border-b border-black/5 bg-surface px-4 py-2.5 md:px-6">
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-ink">{sessionTitle}</div>
        <div className="text-xs text-subtle">祖孙对话 · 实时理解</div>
      </div>
      <div className="flex items-center gap-3">
        <span className="hidden text-xs text-subtle sm:inline">
          已听 {segmentsPlayed}/{totalSegments} 段
        </span>
        <button
          onClick={onReset}
          className="flex items-center gap-1 rounded-full px-2.5 py-1.5 text-xs text-subtle transition hover:bg-slate-100"
          title="重置对话"
        >
          <RotateCcw size={14} /> 重置
        </button>
        <div
          className="flex items-center rounded-full border border-black/10 bg-white p-0.5 text-xs font-medium"
          title="离线:读打包数据、免后端。实时:连 FastAPI 后端(需先启动 uvicorn narrator_flow.server.app:app)"
        >
          <button onClick={() => onModeChange('offline')} className={seg(mode === 'offline')}>
            离线演示
          </button>
          <button onClick={() => onModeChange('backend')} className={seg(mode === 'backend')}>
            实时(后端)
          </button>
        </div>
      </div>
    </header>
  )
}
