import { Settings } from 'lucide-react'

interface Props {
  title: string
  subtitle?: string
  onOpenSettings: () => void
}

export default function TopBar({ title, subtitle, onOpenSettings }: Props) {
  return (
    <header className="flex items-center justify-between border-b border-black/5 bg-surface px-4 py-2.5 md:px-6">
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-ink">{title}</div>
        <div className="text-xs text-subtle">{subtitle ?? '祖孙对话 · 实时理解'}</div>
      </div>
      <button
        onClick={onOpenSettings}
        className="flex flex-none items-center gap-1 rounded-full px-2.5 py-1.5 text-xs text-subtle transition hover:bg-slate-100"
        title="模型配置(API Key / Base URL)"
      >
        <Settings size={15} /> 配置
      </button>
    </header>
  )
}
