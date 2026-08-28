import { useCallback, useEffect, useRef, useState } from 'react'
import type { SessionProvider, SessionSnapshot } from '../api/provider'

/**
 * 驱动一个 SessionProvider,把它返回的快照映射到 React state。
 * Phase 1 只用离线 provider,init 仅执行一次。
 */
export function useSession(makeProvider: () => SessionProvider) {
  const providerRef = useRef<SessionProvider | null>(null)
  const [snap, setSnap] = useState<SessionSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const provider = makeProvider()
    providerRef.current = provider
    setLoading(true)
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
    }
    // 只初始化一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const next = useCallback(() => {
    if (providerRef.current) setSnap(providerRef.current.nextElderSegment())
  }, [])
  const send = useCallback((text: string) => {
    if (providerRef.current) setSnap(providerRef.current.sendGrandchild(text))
  }, [])
  const reset = useCallback(() => {
    if (providerRef.current) setSnap(providerRef.current.reset())
  }, [])

  return { snap, loading, error, next, send, reset }
}
