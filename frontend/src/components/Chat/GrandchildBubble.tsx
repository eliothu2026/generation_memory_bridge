interface Props {
  text: string
}

export default function GrandchildBubble({ text }: Props) {
  return (
    <div className="flex animate-fade-in-up justify-end gap-3">
      <div className="min-w-0 max-w-[80%]">
        <div className="mb-1 text-right text-xs font-medium text-subtle">我(孙辈)</div>
        <div className="inline-block rounded-bubble rounded-tr-[5px] bg-accent-fill px-4 py-3 text-[15px] leading-relaxed text-on-accent shadow-soft">
          {text}
        </div>
      </div>
      <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-ink/5 text-lg">🧑</div>
    </div>
  )
}
