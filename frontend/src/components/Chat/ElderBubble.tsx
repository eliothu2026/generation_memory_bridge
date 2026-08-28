import type { BackgroundNote as BgNote } from '../../types'
import BackgroundNote from './BackgroundNote'
import FollowUpChips from './FollowUpChips'

interface Props {
  text: string
  elderName: string
  backgroundNotes?: BgNote[]
  followUps?: string[]
  onPickFollowUp: (text: string) => void
}

export default function ElderBubble({ text, elderName, backgroundNotes, followUps, onPickFollowUp }: Props) {
  return (
    <div className="flex animate-fade-in-up gap-3">
      <div
        className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-amber-100 text-lg"
        title={elderName}
      >
        👵
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 text-xs font-medium text-subtle">{elderName}</div>
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
