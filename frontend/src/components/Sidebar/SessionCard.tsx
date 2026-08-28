import { MessageSquare } from 'lucide-react'

interface Props {
  title: string
  subtitle?: string
  active?: boolean
  muted?: boolean
}

export default function SessionCard({ title, subtitle, active, muted }: Props) {
  return (
    <div
      className={
        'mb-1 flex cursor-pointer items-start gap-2.5 rounded-xl px-3 py-2.5 transition ' +
        (active ? 'bg-white shadow-soft' : 'hover:bg-black/5') +
        (muted ? ' opacity-60' : '')
      }
      title={muted ? '演示占位' : title}
    >
      <MessageSquare size={16} className={'mt-0.5 flex-none ' + (active ? 'text-accent' : 'text-subtle')} />
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-ink">{title}</div>
        {subtitle && <div className="truncate text-xs text-subtle">{subtitle}</div>}
      </div>
    </div>
  )
}
