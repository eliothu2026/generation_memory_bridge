import { RotateCcw } from 'lucide-react'

interface Props {
  sessionTitle: string
  segmentsPlayed: number
  totalSegments: number
  onReset: () => void
}

export default function TopBar({ sessionTitle, segmentsPlayed, totalSegments, onReset }: Props) {
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
        <span
          className="rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-medium text-subtle"
          title="Phase 2 将接入「实时(后端)」模式"
        >
          ● 离线演示
        </span>
      </div>
    </header>
  )
}
