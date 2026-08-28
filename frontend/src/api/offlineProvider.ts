import type { ChatMessage, DemoScript } from '../types'
import { EMPTY_TIMELINE, type SessionProvider, type SessionSnapshot } from './provider'

let msgCounter = 0
const mkId = () => `m${++msgCounter}`

/**
 * 离线演示数据源:一次 fetch demo_script.json,之后完全在前端逐段回放,
 * 0 后端依赖。老人叙述按脚本推进;孙辈发言为自由输入。
 */
export class OfflineProvider implements SessionProvider {
  private script: DemoScript | null = null
  private cursor = 0 // 已播放的老人段数
  private messages: ChatMessage[] = []
  private readonly url: string

  constructor(url = '/demo_script.json') {
    this.url = url
  }

  async init(): Promise<SessionSnapshot> {
    const res = await fetch(this.url)
    if (!res.ok) throw new Error(`加载 ${this.url} 失败:HTTP ${res.status}`)
    this.script = (await res.json()) as DemoScript
    this.cursor = 0
    this.messages = []
    return this.snapshot()
  }

  nextElderSegment(): SessionSnapshot {
    const script = this.script
    if (script && this.cursor < script.steps.length) {
      const step = script.steps[this.cursor]
      this.messages.push({
        id: mkId(),
        speaker: 'elder',
        text: step.elder_text,
        backgroundNotes: step.new_background_notes.map((t) => ({ text: t, verified: false })),
        followUps: step.follow_ups,
      })
      this.cursor += 1
    }
    return this.snapshot()
  }

  sendGrandchild(text: string): SessionSnapshot {
    const t = text.trim()
    if (t) this.messages.push({ id: mkId(), speaker: 'grandchild', text: t })
    return this.snapshot()
  }

  reset(): SessionSnapshot {
    this.cursor = 0
    this.messages = []
    return this.snapshot()
  }

  private snapshot(): SessionSnapshot {
    const script = this.script
    if (!script) {
      return {
        meta: { id: '', title: '' },
        messages: [],
        timeline: EMPTY_TIMELINE,
        eraEstimate: null,
        segmentsPlayed: 0,
        totalSegments: 0,
      }
    }
    // 时间线/年代 = 最近一段已播放 step 的值(carry-forward 已在生成脚本里完成)。
    const lastPlayed = this.cursor > 0 ? script.steps[this.cursor - 1] : null
    return {
      meta: script.session,
      messages: [...this.messages],
      timeline: lastPlayed ? lastPlayed.timeline : EMPTY_TIMELINE,
      eraEstimate: lastPlayed ? lastPlayed.era_estimate : null,
      segmentsPlayed: this.cursor,
      totalSegments: script.steps.length,
    }
  }
}
