import type { ChatMessage, SessionMeta, Timeline } from '../types'

/** 供 UI 渲染的一份完整会话快照。 */
export interface SessionSnapshot {
  meta: SessionMeta
  messages: ChatMessage[]
  timeline: Timeline
  eraEstimate: string | null
  segmentsPlayed: number
  totalSegments: number
}

/**
 * 数据源抽象:离线(读打包脚本)与后端(FastAPI/WebSocket)共用同一接口,
 * 顶栏切换模式时只需替换实现。所有推进/发言方法返回最新快照。
 */
export interface SessionProvider {
  /** 初始化(可能触发 fetch),返回首个快照。 */
  init(): Promise<SessionSnapshot>
  /** 推进老人的下一段叙述。 */
  nextElderSegment(): SessionSnapshot
  /** 孙辈自由发言(右侧气泡)。 */
  sendGrandchild(text: string): SessionSnapshot
  /** 重置到开头。 */
  reset(): SessionSnapshot
}

export const EMPTY_TIMELINE: Timeline = {
  events: [],
  open_threads: [],
  last_update_mode: null,
  raw_outline_text: '',
}
