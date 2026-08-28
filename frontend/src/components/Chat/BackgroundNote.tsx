import { BookOpen, CheckCircle2 } from 'lucide-react'
import type { BackgroundNote as BgNote } from '../../types'

// 史实补充卡:视觉上明确区别于老人原话,标注为「AI 背景补充」,
// 呼应产品对「幻觉/虚构记忆」风险的护栏——让用户永远分得清哪些是 AI 猜的。
export default function BackgroundNote({ note }: { note: BgNote }) {
  return (
    <div className="animate-fade-in rounded-xl border border-indigo-100 bg-indigo-50/60 px-3.5 py-2.5">
      <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-indigo-700">
        <BookOpen size={13} />
        AI 背景补充
        {note.verified && (
          <span className="ml-1 inline-flex items-center gap-0.5 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
            <CheckCircle2 size={10} /> 据维基核实
          </span>
        )}
        <span className="ml-auto text-[10px] font-normal text-indigo-400">AI 推测/补充,非老人原话</span>
      </div>
      <p className="text-sm leading-relaxed text-slate-700">{note.text}</p>
    </div>
  )
}
