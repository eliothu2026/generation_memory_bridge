import type { TimelineEvent as TEvent } from '../../types'

export default function TimelineEvent({ event }: { event: TEvent }) {
  return (
    <div className="relative animate-fade-in-up pl-8">
      <div className="absolute left-0 top-0 flex h-6 w-6 items-center justify-center rounded-full bg-accent/10 text-[11px] font-semibold text-accent">
        {event.order}
      </div>
      <div className="absolute left-[11px] top-6 h-[calc(100%-1.25rem)] w-px bg-black/5" />
      <div className="pb-4">
        {event.period_hint && (
          <span className="mb-1 inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-subtle">
            {event.period_hint}
          </span>
        )}
        <p className="text-[13.5px] leading-relaxed text-ink">{event.description}</p>
        {event.cause && <p className="mt-1 text-xs text-subtle">因:{event.cause}</p>}
        {event.effect && <p className="mt-0.5 text-xs text-subtle">果:{event.effect}</p>}
      </div>
    </div>
  )
}
