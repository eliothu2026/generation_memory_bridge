import { ChevronLeft, ChevronRight, Clock, HelpCircle, Sparkles } from 'lucide-react'
import type { Timeline } from '../../types'
import TimelineEvent from './TimelineEvent'

const MODE_LABEL: Record<string, string> = {
  incremental: '增量更新',
  refine: '轻整理',
  full_rerun: '全量重跑',
}

interface Props {
  timeline: Timeline
  eraEstimate: string | null
  collapsed: boolean
  onToggle: () => void
  segmentsPlayed: number
  totalSegments: number
}

export default function TimelinePanel({
  timeline,
  eraEstimate,
  collapsed,
  onToggle,
  segmentsPlayed,
  totalSegments,
}: Props) {
  if (collapsed) {
    return (
      <button
        onClick={onToggle}
        className="flex w-12 flex-none flex-col items-center gap-3 border-l border-black/5 bg-surface py-4 text-subtle transition hover:bg-slate-50"
        title="展开时间线"
      >
        <ChevronLeft size={18} />
        <Clock size={18} className="text-accent" />
        <span className="mt-1 text-xs [writing-mode:vertical-rl]">时间线</span>
      </button>
    )
  }

  const events = [...timeline.events].sort((a, b) => a.order - b.order)

  return (
    <aside className="flex w-80 flex-none flex-col border-l border-black/5 bg-surface lg:w-96">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-ink">
          <Clock size={16} className="text-accent" /> 时间线 · 逻辑梳理
        </div>
        <button onClick={onToggle} className="rounded-full p-1 text-subtle hover:bg-slate-100" title="收起">
          <ChevronRight size={18} />
        </button>
      </div>

      {eraEstimate && (
        <div className="mx-4 mb-2 flex items-start gap-1.5 rounded-lg bg-accent/5 px-3 py-2 text-xs text-accent">
          <Sparkles size={13} className="mt-0.5 flex-none" />
          <span>
            <span className="font-medium">AI 推测年代:</span>
            {eraEstimate}
          </span>
        </div>
      )}

      <div className="flex items-center gap-2 px-4 pb-2 text-[11px] text-subtle">
        <span>
          已听 {segmentsPlayed}/{totalSegments} 段
        </span>
        {timeline.last_update_mode && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5">
            {MODE_LABEL[timeline.last_update_mode] ?? timeline.last_update_mode}
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 pt-2">
        {events.length === 0 ? (
          <p className="mt-10 text-center text-sm leading-relaxed text-subtle">
            老人开始讲述后,
            <br />
            这里会实时长出时间线…
          </p>
        ) : (
          <div>
            {events.map((e) => (
              <TimelineEvent key={e.order} event={e} />
            ))}
          </div>
        )}

        {timeline.open_threads.length > 0 && (
          <div className="mt-4 border-t border-black/5 pt-3">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-subtle">
              <HelpCircle size={13} /> 待澄清线索
            </div>
            <ul className="flex flex-col gap-1.5 pb-6">
              {timeline.open_threads.map((t, i) => (
                <li key={i} className="rounded-lg bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
                  {t}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </aside>
  )
}
