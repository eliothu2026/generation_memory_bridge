// 前端类型:镜像 src/narrator_flow/state.py 的字段 + demo_script.json 的结构。

export interface TimelineEvent {
  order: number
  period_hint: string | null
  description: string
  cause: string | null
  effect: string | null
  source_chunk_indices: number[]
}

export interface Timeline {
  events: TimelineEvent[]
  open_threads: string[]
  last_update_mode: string | null
  raw_outline_text: string
}

export interface DemoStep {
  index: number
  elder_text: string
  new_background_notes: string[]
  era_estimate: string | null
  follow_ups: string[]
  timeline: Timeline
}

export interface SessionMeta {
  id: string
  title: string
  subtitle?: string
  elder_name?: string
}

export interface DemoScript {
  session: SessionMeta
  steps: DemoStep[]
}

export type Speaker = 'elder' | 'grandchild'

/** 一条背景补充笔记;verified 为真实模式下的「据维基核实」标记(demo 里恒为 false)。 */
export interface BackgroundNote {
  text: string
  verified?: boolean
}

/** 对话流里的一条消息。elder 消息会额外携带该段挂载的背景补充与交互提醒。 */
export interface ChatMessage {
  id: string
  speaker: Speaker
  text: string
  backgroundNotes?: BackgroundNote[]
  followUps?: string[]
}
