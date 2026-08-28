// 会话管理的 REST 封装(对接后端 /api/sessions 持久化多会话)。

export interface SessionSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export async function listSessions(): Promise<SessionSummary[]> {
  const r = await fetch('/api/sessions')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function createSession(): Promise<string> {
  const r = await fetch('/api/sessions', { method: 'POST' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return (await r.json()).id
}

export async function deleteSession(id: string): Promise<void> {
  const r = await fetch(`/api/sessions/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
}
