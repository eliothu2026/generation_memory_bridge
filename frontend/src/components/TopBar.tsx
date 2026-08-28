import { RotateCcw } from 'lucide-react'
import type { LiveInput, TopMode } from '../api/provider'

interface Props {
  sessionTitle: string
  segmentsPlayed: number
  totalSegments: number
  onReset: () => void
  topMode: TopMode
  liveInput: LiveInput
  onTopModeChange: (m: TopMode) => void
  onLiveInputChange: (i: LiveInput) => void
}

export default function TopBar({
  sessionTitle,
  segmentsPlayed,
  totalSegments,
  onReset,
  topMode,
  liveInput,
  onTopModeChange,
  onLiveInputChange,
}: Props) {
  const seg = (active: boolean) =>
    'rounded-full px-3 py-1 transition ' +
    (active ? 'bg-accent text-white shadow-soft' : 'text-subtle hover:text-ink')
  const subSeg = (active: boolean) =>
    'rounded-full px-2.5 py-1 transition ' +
    (active ? 'bg-white text-ink shadow-soft' : 'text-subtle hover:text-ink')

  const isVoice = topMode === 'live' && liveInput === 'voice'

  return (
    <header className="flex items-center justify-between border-b border-black/5 bg-surface px-4 py-2.5 md:px-6">
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-ink">{sessionTitle}</div>
        <div className="text-xs text-subtle">祖孙对话 · 实时理解</div>
      </div>
      <div className="flex items-center gap-2.5">
        {!isVoice && (
          <span className="hidden text-xs text-subtle lg:inline">
            已听 {segmentsPlayed}/{totalSegments} 段
          </span>
        )}
        {!isVoice && (
          <button
            onClick={onReset}
            className="flex items-center gap-1 rounded-full px-2.5 py-1.5 text-xs text-subtle transition hover:bg-slate-100"
            title="重置对话"
          >
            <RotateCcw size={14} /> 重置
          </button>
        )}

        {/* 顶层:演示 / 实时(平级) */}
        <div
          className="flex items-center rounded-full border border-black/10 bg-white p-0.5 text-xs font-medium"
          title="演示:读打包数据、免后端。实时(后端):连 FastAPI,用真实 DeepSeek 分析"
        >
          <button onClick={() => onTopModeChange('demo')} className={seg(topMode === 'demo')}>
            演示模式
          </button>
          <button onClick={() => onTopModeChange('live')} className={seg(topMode === 'live')}>
            实时(后端)
          </button>
        </div>

        {/* 次级:仅「实时(后端)」下出现 —— 文字模拟 / 真实语音 */}
        {topMode === 'live' && (
          <div
            className="flex animate-fade-in items-center rounded-full bg-slate-100 p-0.5 text-xs font-medium"
            title="文字模拟:手输长辈口述。真实语音:上传录音→ASR→背压→分析"
          >
            <button onClick={() => onLiveInputChange('text')} className={subSeg(liveInput === 'text')}>
              💬 文字模拟
            </button>
            <button onClick={() => onLiveInputChange('voice')} className={subSeg(liveInput === 'voice')}>
              🎙️ 真实语音
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
