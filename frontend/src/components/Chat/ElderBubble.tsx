import { Mic } from 'lucide-react'
import type { BackgroundNote as BgNote } from '../../types'
import BackgroundNote from './BackgroundNote'
import FollowUpChips from './FollowUpChips'

interface Props {
  text: string
  elderName: string
  backgroundNotes?: BgNote[]
  followUps?: string[]
  coalescedFrom?: number
  onPickFollowUp: (text: string) => void
}

export default function ElderBubble({
  text,
  elderName,
  backgroundNotes,
  followUps,
  coalescedFrom,
  onPickFollowUp,
}: Props) {
  return (
    <div className="flex animate-fade-in-up gap-3">
      <div
        className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-amber-100 text-lg"
        title={elderName}
      >
        👵
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center gap-2 text-xs font-medium text-subtle">
          {elderName}
          {coalescedFrom != null && coalescedFrom > 0 && (
            <span
              className="inline-flex items-center gap-0.5 rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-subtle"
              title="该段由多个 ASR 片段经背压合并队列合并而来"
            >
              <Mic size={10} /> 合并自 {coalescedFrom} 段
            </span>
          )}
        </div>
        <div className="inline-block max-w-full rounded-2xl rounded-tl-md bg-[#f1f3f4] px-4 py-3 text-[15px] leading-relaxed text-ink">
          {text}
        </div>

        {backgroundNotes && backgroundNotes.length > 0 && (
          <div className="mt-2 flex flex-col gap-2">
            {backgroundNotes.map((n, i) => (
              <BackgroundNote key={i} note={n} />
            ))}
          </div>
        )}

        {followUps && followUps.length > 0 && <FollowUpChips items={followUps} onPick={onPickFollowUp} />}
      </div>
    </div>
  )
}
