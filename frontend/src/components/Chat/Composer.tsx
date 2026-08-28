import { ArrowRight, Loader2, Send } from 'lucide-react'
import type { Mode } from '../../api/provider'

interface Props {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  onNext: () => void
  canAdvance: boolean
  busy: boolean
  mode: Mode
  speaker: 'elder' | 'grandchild'
  onSpeakerChange: (s: 'elder' | 'grandchild') => void
}

export default function Composer({
  value,
  onChange,
  onSend,
  onNext,
  canAdvance,
  busy,
  mode,
  speaker,
  onSpeakerChange,
}: Props) {
  const backend = mode === 'backend'
  const placeholder = backend
    ? speaker === 'elder'
      ? '以长辈身份说一段往事…(AI 会实时整理)'
      : '替孙辈说点什么…'
    : '替孙辈说点什么…(回车发送)'

  const chip = (active: boolean, tone: 'amber' | 'blue') =>
    'rounded-full px-2.5 py-0.5 transition ' +
    (active
      ? tone === 'amber'
        ? 'bg-amber-100 text-amber-900'
        : 'bg-blue-100 text-blue-900'
      : 'text-subtle hover:text-ink')

  return (
    <div className="border-t border-black/5 bg-surface px-4 py-3 md:px-10">
      <div className="mx-auto max-w-3xl">
        {backend && (
          <div className="mb-2 flex items-center gap-1.5 text-xs">
            <span className="text-subtle">以谁的身份说:</span>
            <div className="flex items-center rounded-full border border-black/10 bg-white p-0.5 font-medium">
              <button onClick={() => onSpeakerChange('elder')} className={chip(speaker === 'elder', 'amber')}>
                👵 老人
              </button>
              <button onClick={() => onSpeakerChange('grandchild')} className={chip(speaker === 'grandchild', 'blue')}>
                🧑 我
              </button>
            </div>
            {speaker === 'elder' && <span className="text-[11px] text-subtle">· 真实模型分析,约 1–2 分钟</span>}
          </div>
        )}

        <div className="flex items-center gap-2">
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
              disabled={busy}
              placeholder={placeholder}
              className="min-w-0 flex-1 bg-transparent text-[15px] text-ink outline-none placeholder:text-subtle disabled:opacity-60"
            />
            <button
              onClick={onSend}
              disabled={!value.trim() || busy}
              className="flex h-8 w-8 flex-none items-center justify-center rounded-full text-accent transition enabled:hover:bg-accent/10 disabled:text-slate-300"
              title="发送"
            >
              {busy ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}
            </button>
          </div>

          {!backend && (
            <button
              onClick={onNext}
              disabled={!canAdvance || busy}
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
          )}
        </div>
      </div>
    </div>
  )
}
