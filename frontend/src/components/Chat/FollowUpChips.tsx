import { Lightbulb } from 'lucide-react'

interface Props {
  items: string[]
  onPick: (text: string) => void
}

// 交互提醒:AI 替年轻人想的追问,点击即填入输入框(不自动发送)。
export default function FollowUpChips({ items, onPick }: Props) {
  return (
    <div className="mt-2.5 animate-fade-in">
      <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-amber-700">
        <Lightbulb size={13} /> 你可以这样接
        <span className="text-[10px] font-normal text-subtle">· 点击填入输入框</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {items.map((q, i) => (
          <button
            key={i}
            onClick={() => onPick(q)}
            className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-left text-[13px] text-amber-900 transition hover:border-amber-300 hover:bg-amber-100"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
