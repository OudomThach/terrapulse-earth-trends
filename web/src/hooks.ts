/** Small reusable hooks. */

import { useEffect, useState, useSyncExternalStore } from 'react'
import { getStats, subscribeStats, type ApiStats } from './api/client'

export interface AsyncState<T> {
  data: T | undefined
  error: Error | null
  loading: boolean
}

/** Run an async loader whenever ``deps`` change. Keeps the previous data on screen while the next
 *  request is in flight (stale-while-revalidate), which is what makes the interface feel smooth. */
export function useAsync<T>(load: () => Promise<T>, deps: readonly unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ data: undefined, error: null, loading: true })
  useEffect(() => {
    let alive = true
    setState((s) => ({ ...s, loading: true, error: null }))
    load().then(
      (data) => alive && setState({ data, error: null, loading: false }),
      (error: Error) => alive && setState((s) => ({ data: s.data, error, loading: false })),
    )
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

/** Live API statistics (latency, cache hits). */
export function useApiStats(): ApiStats {
  return useSyncExternalStore(subscribeStats, getStats)
}

/** A value that follows ``value`` after it has been stable for ``ms`` (used for sliders). */
export function useDebounced<T>(value: T, ms = 180): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms)
    return () => clearTimeout(id)
  }, [value, ms])
  return v
}

/** Re-render on a timer while ``active`` (used to poll a background computation). */
export function useInterval(callback: () => void, ms: number, active: boolean): void {
  useEffect(() => {
    if (!active) return
    const id = setInterval(callback, ms)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ms, active])
}
