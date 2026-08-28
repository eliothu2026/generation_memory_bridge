import { useCallback, useEffect, useRef, useState } from 'react'
import { BackendProvider } from '../api/backendProvider'
import { OfflineProvider } from '../api/offlineProvider'
import type { Mode, SessionProvider, SessionSnapshot } from '../api/provider'

/**
 * 按当前模式驱动一个 SessionProvider。切换模式时会销毁旧 provider(关 WS)、
 * 用新实现重新 init。所有动作方法都是异步的。
 */
export function useSession(mode: Mode) {
  const providerRef = useRef<SessionProvider | null>(null)
  const [snap, setSnap] = useState<SessionSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    // 音频 / 实时麦克风模式由各自组件自行管理(上传/采麦 + WS 流式),此处不建 provider
    if (mode === 'audio' || mode === 'mic') {
      providerRef.current = null
      setSnap(null)
      setError(null)
      setLoading(false)
      return
    }
    const provider: SessionProvider =
      mode === 'backend' ? new BackendProvider() : new OfflineProvider()
    providerRef.current = provider
    setLoading(true)
    setError(null)
    setSnap(null)
    provider
      .init()
      .then((s) => {
        if (!cancelled) {
          setSnap(s)
          setLoading(false)
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e))
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
      provider.dispose?.()
    }
  }, [mode])

  const next = useCallback(async () => {
    const p = providerRef.current
    if (!p) return
    try {
      setSnap(await p.nextElderSegment())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const send = useCallback(async (text: string) => {
    const p = providerRef.current
    if (!p) return
    try {
      setSnap(await p.sendGrandchild(text))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const submitElder = useCallback(async (text: string) => {
    const p = providerRef.current
    if (!p || !p.submitElder) return
    try {
      setSnap(await p.submitElder(text))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const reset = useCallback(async () => {
    const p = providerRef.current
    if (!p) return
    try {
      setSnap(await p.reset())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  return { snap, loading, error, next, send, submitElder, reset }
}
