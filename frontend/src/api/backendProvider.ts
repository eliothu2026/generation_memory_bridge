import type { SessionProvider, SessionSnapshot } from './provider'

/**
 * 实时(后端)数据源:REST 建会话 + WebSocket 逐段推进。
 * 与 Vite 的 proxy 配合:/api 与 /ws 会被转发到 FastAPI(默认 localhost:8000)。
 *
 * 协议:连接后服务端先推一帧初始快照;之后每次发送 {type} 指令,服务端回推一帧快照。
 * 这里用一个 pending 队列把"发送 → 下一帧快照"配成请求/响应。
 */
export class BackendProvider implements SessionProvider {
  private ws: WebSocket | null = null
  private id = ''
  private pending: Array<(s: SessionSnapshot) => void> = []

  async init(): Promise<SessionSnapshot> {
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'demo' }),
    })
    if (!res.ok) throw new Error(`创建会话失败:HTTP ${res.status}(后端是否已启动?)`)
    const data = await res.json()
    this.id = data.id
    return await this.openWs()
  }

  private openWs(): Promise<SessionSnapshot> {
    return new Promise((resolve, reject) => {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${location.host}/ws/sessions/${this.id}`)
      this.ws = ws
      let opened = false
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data as string)
        if (msg.type === 'snapshot') {
          const snap = msg.snapshot as SessionSnapshot
          if (!opened) {
            opened = true
            resolve(snap) // 连接后的第一帧 = 初始快照
          } else {
            const r = this.pending.shift()
            if (r) r(snap)
          }
        } else if (msg.type === 'error' && !opened) {
          reject(new Error(msg.message || '会话错误'))
        }
      }
      ws.onerror = () => {
        if (!opened) reject(new Error('WebSocket 连接失败(后端是否已启动?)'))
      }
    })
  }

  private request(payload: object): Promise<SessionSnapshot> {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket 未连接'))
        return
      }
      this.pending.push(resolve)
      this.ws.send(JSON.stringify(payload))
    })
  }

  nextElderSegment(): Promise<SessionSnapshot> {
    return this.request({ type: 'next_elder' })
  }

  sendGrandchild(text: string): Promise<SessionSnapshot> {
    return this.request({ type: 'grandchild', text })
  }

  reset(): Promise<SessionSnapshot> {
    return this.request({ type: 'reset' })
  }

  dispose(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.pending = []
  }
}
