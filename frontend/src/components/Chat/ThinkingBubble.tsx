// 「正在识别和理解…」占位:老人说完一段、结果还没回来的那 1–2 分钟里,
// 在对话流里挂一个气泡,让用户知道这段已经被收到、正在处理(与静态 demo 同款)。
interface Props {
  label?: string
  hint?: string
}

export default function ThinkingBubble({ label = '正在识别和理解…', hint }: Props) {
  return (
    <div className="flex animate-fade-in-up gap-3">
      <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-ink/5 text-lg">👵</div>
      <div className="min-w-0 flex-1">
        <span className="inline-flex items-center gap-2.5 rounded-bubble rounded-tl-[5px] bg-elder px-4 py-3 text-sm text-subtle shadow-soft">
          <span className="flex items-center gap-1">
            <span className="block h-1.5 w-1.5 animate-dot rounded-full bg-accent" />
            <span
              className="block h-1.5 w-1.5 animate-dot rounded-full bg-accent"
              style={{ animationDelay: '0.15s' }}
            />
            <span
              className="block h-1.5 w-1.5 animate-dot rounded-full bg-accent"
              style={{ animationDelay: '0.3s' }}
            />
          </span>
          {label}
        </span>
        {hint && <div className="mt-1.5 pl-1 text-[11px] text-faint">{hint}</div>}
      </div>
    </div>
  )
}
