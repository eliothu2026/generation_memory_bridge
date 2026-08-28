import type { SessionProvider, SessionSnapshot } from './provider'

/**
 * 实时(后端)数据源占位。将在 Phase 2 接通 FastAPI + WebSocket:
 *   init         -> POST /api/sessions 建会话,GET 拉初始状态
 *   nextElderSegment / sendGrandchild -> 经 WS 发消息,服务端回推 state
 * 目前仅抛出提示,顶栏「实时」模式暂不可用。
 */
export class BackendProvider implements SessionProvider {
  async init(): Promise<SessionSnapshot> {
    throw new Error('「实时(后端)」模式将在 Phase 2 接入,请先使用「离线演示」模式。')
  }
  nextElderSegment(): SessionSnapshot {
    throw new Error('Phase 2 未实现')
  }
  sendGrandchild(): SessionSnapshot {
    throw new Error('Phase 2 未实现')
  }
  reset(): SessionSnapshot {
    throw new Error('Phase 2 未实现')
  }
}
