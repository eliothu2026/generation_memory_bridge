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

const MODES: { key: Mode; label: string }[] = [
  { key: 'offline', label: '离线演示' },
  { key: 'backend', label: '实时(后端)' },
  { key: 'audio', label: '🎙️ 音频' },
]

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
        {mode !== 'audio' && (
          <span className="hidden text-xs text-subtle sm:inline">
            已听 {segmentsPlayed}/{totalSegments} 段
          </span>
        )}
        {mode !== 'audio' && (
          <button
            onClick={onReset}
            className="flex items-center gap-1 rounded-full px-2.5 py-1.5 text-xs text-subtle transition hover:bg-slate-100"
            title="重置对话"
          >
            <RotateCcw size={14} /> 重置
          </button>
        )}
        <div
          className="flex items-center rounded-full border border-black/10 bg-white p-0.5 text-xs font-medium"
          title="离线:读打包数据、免后端。实时:自由输入 + 真实 DeepSeek。音频:上传录音→ASR→背压→分析(均需后端/key)"
        >
          {MODES.map((m) => (
            <button key={m.key} onClick={() => onModeChange(m.key)} className={seg(mode === m.key)}>
              {m.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}
