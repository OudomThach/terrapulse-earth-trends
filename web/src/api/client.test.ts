import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// The client keeps module-level caches, so import a fresh copy for every test.
async function freshClient() {
  vi.resetModules()
  return import('./client')
}

function jsonResponse(body: unknown, init: { status?: number; ms?: string } = {}): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200, headers: { 'Content-Type': 'application/json', 'X-Response-Time-ms': init.ms ?? '12.4' },
  })
}

describe('api client', () => {
  const fetchMock = vi.fn()
  beforeEach(() => vi.stubGlobal('fetch', fetchMock))
  afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals() })

  it('returns parsed JSON and records server latency', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ a: 1 }))
    const c = await freshClient()
    expect(await c.get<{ a: number }>('/x')).toEqual({ a: 1 })
    expect(c.getStats()).toMatchObject({ calls: 1, lastServerMs: 12 })
  })

  it('de-duplicates identical in-flight requests', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ok: true }))
    const c = await freshClient()
    await Promise.all([c.get('/same'), c.get('/same'), c.get('/same')])
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('serves repeat GETs from the cache and counts them as instant', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ n: 1 }))
    const c = await freshClient()
    await c.get('/cached')
    await c.get('/cached')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(c.getStats().cacheHits).toBe(1)
  })

  it('bypasses the cache when asked for fresh data', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ n: Math.random() })))
    const c = await freshClient()
    await c.get('/fresh', { fresh: true })
    await c.get('/fresh', { fresh: true })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('turns an error response into an ApiError with the server message', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: 'Unknown place' }, { status: 404 }))
    const c = await freshClient()
    await expect(c.get('/bad')).rejects.toMatchObject({ name: 'ApiError', status: 404, message: 'Unknown place' })
  })

  it('does not cache failures, so a retry can succeed', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'boom' }, { status: 503 })).mockResolvedValueOnce(jsonResponse({ ok: 1 }))
    const c = await freshClient()
    await expect(c.get('/flaky')).rejects.toThrow('boom')
    expect(await c.get('/flaky')).toEqual({ ok: 1 })
  })

  it('posts JSON bodies', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: 7 }))
    const c = await freshClient()
    expect(await c.post<{ id: number }>('/save', { a: 1 })).toEqual({ id: 7 })
    const [, init] = fetchMock.mock.calls[0]!
    expect(init).toMatchObject({ method: 'POST', body: '{"a":1}' })
  })
})
