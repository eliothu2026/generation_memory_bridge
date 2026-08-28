import type { SessionProvider, SessionSnapshot } from './provider'

/**
 * 实时(后端)数据源:REST 建 **real 会话** + WebSocket。
 * real 会话 = 自由输入 + 真实 DeepSeek 分析(后端需 DEEPSEEK_API_KEY)。
 * 与 Vite 的 proxy 配合:/api 与 /ws 转发到 FastAPI(默认 localhost:8000)。
 *
 * 协议:连接后服务端先推一帧初始快照;之后每发一条指令,服务端回推一帧快照。
 * 这里用 pending 队列把"发送 → 下一帧快照"配成请求/响应。
 */
export class BackendProvider implements SessionProvider {
  private ws: WebSocket | null = null
  private id = ''
  private pending: Array<(s: SessionSnapshot) => void> = []

  async init(): Promise<SessionSnapshot> {
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'real' }),
    })
    if (!res.ok) {
      let detail = `HTTP ${res.status}`
      try {
        const j = await res.json()
        if (j.detail) detail = j.detail
      } catch {
        /* ignore */
      }
      throw new Error(`${detail}(实时模式需后端已启动并配置 DEEPSEEK_API_KEY)`)
    }
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

  submitElder(text: string): Promise<SessionSnapshot> {
    return this.request({ type: 'elder_text', text })
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
