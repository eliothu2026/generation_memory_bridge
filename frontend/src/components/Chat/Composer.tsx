import { ArrowRight, Send } from 'lucide-react'

interface Props {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  onNext: () => void
  canAdvance: boolean
}

export default function Composer({ value, onChange, onSend, onNext, canAdvance }: Props) {
  return (
    <div className="border-t border-black/5 bg-surface px-4 py-3 md:px-10">
      <div className="mx-auto flex max-w-3xl items-center gap-2">
        <div className="flex flex-1 items-center gap-2 rounded-full border border-black/10 bg-white px-4 py-2 shadow-soft focus-within:border-accent/40">
          <input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
                e.preventDefault()
                onSend()
              }
            }}
            placeholder="替孙辈说点什么…(回车发送)"
            className="min-w-0 flex-1 bg-transparent text-[15px] text-ink outline-none placeholder:text-subtle"
          />
          <button
            onClick={onSend}
            disabled={!value.trim()}
            className="flex h-8 w-8 flex-none items-center justify-center rounded-full text-accent transition enabled:hover:bg-accent/10 disabled:text-slate-300"
            title="发送"
          >
            <Send size={17} />
          </button>
        </div>
        <button
          onClick={onNext}
          disabled={!canAdvance}
          className="flex flex-none items-center gap-1.5 rounded-full bg-accent px-4 py-2.5 text-sm font-medium text-white shadow-soft transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
        >
          {canAdvance ? (
            <>
              老人继续讲 <ArrowRight size={16} />
            </>
          ) : (
            '讲完了'
          )}
        </button>
      </div>
    </div>
  )
}
