/** A small typed fetch layer: de-duplicates identical requests, caches GETs for the session, and records
 *  latency so the interface can show real numbers. */

/** Error thrown for a failed API call; carries the HTTP status and the server's message. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export interface ApiStats {
  calls: number
  cacheHits: number
  lastServerMs: number | null
  lastRoundTripMs: number | null
}

let stats: ApiStats = { calls: 0, cacheHits: 0, lastServerMs: null, lastRoundTripMs: null }
const listeners = new Set<() => void>()
const cache = new Map<string, unknown>()
const inflight = new Map<string, Promise<unknown>>()

function update(patch: Partial<ApiStats>): void {
  stats = { ...stats, ...patch }
  listeners.forEach((l) => l())
}

/** For useSyncExternalStore. */
export function subscribeStats(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Return live request statistics (last latency, cached and instant counts) for the latency label. */
export function getStats(): ApiStats {
  return stats
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const t0 = performance.now()
  const res = await fetch(path, init)
  const roundTrip = performance.now() - t0
  const serverMs = Number(res.headers.get('X-Response-Time-ms'))
  update({
    calls: stats.calls + 1,
    lastRoundTripMs: Math.round(roundTrip),
    lastServerMs: Number.isFinite(serverMs) && serverMs > 0 ? Math.round(serverMs) : stats.lastServerMs,
  })
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg?: string }) => d.msg).join('; ')
    } catch {
      /* keep the status text */
    }
    throw new ApiError(res.status, message)
  }
  return (await res.json()) as T
}

/** GET with caching and request de-duplication. Pass ``fresh`` to bypass the cache. */
export function get<T>(path: string, opts: { fresh?: boolean } = {}): Promise<T> {
  if (!opts.fresh && cache.has(path)) {
    update({ cacheHits: stats.cacheHits + 1 })
    return Promise.resolve(cache.get(path) as T)
  }
  const pending = inflight.get(path)
  if (pending) return pending as Promise<T>
  const promise = request<T>(path)
    .then((data) => {
      if (!opts.fresh) cache.set(path, data)
      return data
    })
    .finally(() => inflight.delete(path))
  inflight.set(path, promise)
  return promise
}

/** POST a JSON body to the API and return the typed reply. */
export function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/** Warm the cache without caring about the result (used to prefetch likely next views). */
export function prefetch(path: string): void {
  void get(path).catch(() => undefined)
}
