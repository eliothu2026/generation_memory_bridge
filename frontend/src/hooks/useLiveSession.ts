import { useCallback, useEffect, useRef, useState } from 'react'
import type { SessionSnapshot } from '../api/provider'

/**
 * 驱动一条持久化会话的实时通道:连 /ws/sessions/{id},被动接收服务端推送的快照。
 * 老人输入(文字/音频)由服务端分析后回推快照;孙辈发言即时回推。
 */
export function useLiveSession(id: string) {
  const [snap, setSnap] = useState<SessionSnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let cancelled = false
    setSnap(null)
    setError(null)
    setNotice(null)
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${location.host}/ws/sessions/${id}`)
    wsRef.current = ws
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data as string)
      if (m.type === 'snapshot') setSnap(m.snapshot)
      else if (m.type === 'error') setError(m.message)
      else if (m.type === 'status') setNotice(m.message)
    }
    ws.onerror = () => {
      if (!cancelled) setError('WebSocket 连接失败(后端是否已启动?)')
    }
    return () => {
      cancelled = true
      ws.close()
    }
  }, [id])

  const sendElderText = useCallback((t: string) => {
    const ws = wsRef.current
    const text = t.trim()
    if (ws && ws.readyState === WebSocket.OPEN && text) {
      setError(null)
      ws.send(JSON.stringify({ type: 'elder_text', text }))
    }
  }, [])

  const sendGrandchild = useCallback((t: string) => {
    const ws = wsRef.current
    const text = t.trim()
    if (ws && ws.readyState === WebSocket.OPEN && text) {
      ws.send(JSON.stringify({ type: 'grandchild', text }))
    }
  }, [])

  const sendAudio = useCallback((blob: Blob) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN && blob.size > 0) {
      setError(null)
      ws.send(blob)
    }
  }, [])

  return { snap, error, notice, sendElderText, sendGrandchild, sendAudio }
}
