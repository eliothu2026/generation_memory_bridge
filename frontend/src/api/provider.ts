import type { ChatMessage, SessionMeta, Timeline } from '../types'

/** 供 UI 渲染的一份完整会话快照(离线与后端两种数据源共用同一结构)。 */
export interface SessionSnapshot {
  meta: SessionMeta
  messages: ChatMessage[]
  timeline: Timeline
  eraEstimate: string | null
  segmentsPlayed: number
  totalSegments: number
}

export type Mode = 'offline' | 'backend' | 'audio'

/**
 * 数据源抽象:离线(读打包脚本)与后端(FastAPI/WebSocket)共用同一接口。
 * 所有方法都是异步的(后端走网络/WS)。
 */
export interface SessionProvider {
  /** 初始化(fetch / 建会话 / 连 WS),返回首个快照。 */
  init(): Promise<SessionSnapshot>
  /** 推进老人的下一段叙述(脚本模式)。 */
  nextElderSegment(): Promise<SessionSnapshot>
  /** 提交一段自由输入的老人叙述(后端 real 会话:真实 DeepSeek 分析)。 */
  submitElder?(text: string): Promise<SessionSnapshot>
  /** 孙辈自由发言(右侧气泡)。 */
  sendGrandchild(text: string): Promise<SessionSnapshot>
  /** 重置到开头。 */
  reset(): Promise<SessionSnapshot>
  /** 释放资源(如关闭 WebSocket)。 */
  dispose?(): void
}

export const EMPTY_TIMELINE: Timeline = {
  events: [],
  open_threads: [],
  last_update_mode: null,
  raw_outline_text: '',
}
