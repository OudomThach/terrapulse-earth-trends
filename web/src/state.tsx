/** App-wide state, kept in the address bar so every view is a shareable link. */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { PlaceRef, YearSpan } from './api/endpoints'
import { clamp } from './lib/format'

export const FIRST_YEAR = 1990
export const LAST_YEAR = 2025
export const CUSTOM = 'custom'

export type View = 'detective' | 'risk' | 'project'
export type Stage = 'suspects' | 'evidence' | 'world' | 'links' | 'how'
export type RiskTab = 'forecast' | 'fire' | 'history'

export const STAGES: { id: Stage; label: string }[] = [
  { id: 'suspects', label: 'Suspects' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'world', label: 'Around the world' },
  { id: 'links', label: 'Connections' },
  { id: 'how', label: 'How it works' },
]

export interface AppState {
  view: View
  stage: Stage
  place: string // a place name, or CUSTOM
  lat: number
  lon: number
  start: number
  end: number
  question: string | null // question id, 'surprise', or null for "all clues"
  code: string
  mapCode: string
  mapFollows: boolean // the world map shows the investigated variable until the user picks another
  riskTab: RiskTab
  region: string
  horizon: number
}

export const DEFAULTS: AppState = {
  view: 'detective', stage: 'suspects', place: 'Svalbard, Arctic', lat: 13.1, lon: 103.2,
  start: FIRST_YEAR, end: LAST_YEAR, question: null, code: 'T2M', mapCode: 'T2M', mapFollows: true, riskTab: 'forecast',
  region: 'Battambang, Cambodia', horizon: 14,
}

const oneOf = <T extends string>(v: string | null, options: readonly T[], fallback: T): T =>
  options.includes(v as T) ? (v as T) : fallback

const num = (v: string | null, fallback: number, lo: number, hi: number): number => {
  const n = Number(v)
  return v !== null && v !== '' && Number.isFinite(n) ? clamp(n, lo, hi) : fallback
}

/** Read state from a query string, falling back to defaults for anything missing or invalid. */
export function parseState(search: string): AppState {
  const q = new URLSearchParams(search)
  const start = Math.round(num(q.get('from'), DEFAULTS.start, FIRST_YEAR, LAST_YEAR))
  const end = Math.round(num(q.get('to'), DEFAULTS.end, FIRST_YEAR, LAST_YEAR))
  return {
    view: oneOf(q.get('view'), ['detective', 'risk', 'project'] as const, DEFAULTS.view),
    stage: oneOf(q.get('stage'), STAGES.map((s) => s.id), DEFAULTS.stage),
    place: q.get('place') || DEFAULTS.place,
    lat: num(q.get('lat'), DEFAULTS.lat, -90, 90),
    lon: num(q.get('lon'), DEFAULTS.lon, -180, 180),
    start: end - start >= 9 ? start : DEFAULTS.start,
    end: end - start >= 9 ? end : DEFAULTS.end,
    question: q.get('q') || null,
    code: q.get('var') || DEFAULTS.code,
    mapCode: q.get('map') || q.get('var') || DEFAULTS.mapCode,
    mapFollows: !q.has('map'),
    riskTab: oneOf(q.get('risk'), ['forecast', 'fire', 'history'] as const, DEFAULTS.riskTab),
    region: q.get('region') || DEFAULTS.region,
    horizon: Math.round(num(q.get('horizon'), DEFAULTS.horizon, 7, 28)),
  }
}

/** Write only the values that differ from the defaults, so links stay short. */
export function serializeState(s: AppState): string {
  const q = new URLSearchParams()
  const add = (key: string, value: string | number | null, def: string | number | null) => {
    if (value !== null && value !== def) q.set(key, String(value))
  }
  add('view', s.view, DEFAULTS.view)
  add('stage', s.stage, DEFAULTS.stage)
  add('place', s.place, DEFAULTS.place)
  if (s.place === CUSTOM) {
    q.set('lat', String(s.lat))
    q.set('lon', String(s.lon))
  }
  add('from', s.start, DEFAULTS.start)
  add('to', s.end, DEFAULTS.end)
  add('q', s.question, null)
  add('var', s.code, DEFAULTS.code)
  if (s.stage === 'world') add('map', s.mapCode, s.code)
  add('risk', s.riskTab, DEFAULTS.riskTab)
  add('region', s.region, DEFAULTS.region)
  add('horizon', s.horizon, DEFAULTS.horizon)
  const text = q.toString()
  return text ? `?${text}` : ''
}

interface Ctx {
  state: AppState
  patch: (p: Partial<AppState>) => void
  placeRef: PlaceRef
  years: YearSpan
}

const AppContext = createContext<Ctx | null>(null)

/** Holds the whole app state and keeps it in sync with the address bar, so every view is a shareable link. */
export function AppStateProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppState>(() => parseState(window.location.search))
  const patch = useCallback(
    (p: Partial<AppState>) =>
      setState((s) => {
        const next = { ...s, ...p }
        if (p.code !== undefined && p.mapCode === undefined && s.mapFollows) next.mapCode = p.code // map follows the clue
        return next
      }),
    [],
  )

  useEffect(() => {
    const url = `${window.location.pathname}${serializeState(state)}`
    window.history.replaceState(null, '', url)
  }, [state])

  const value = useMemo<Ctx>(
    () => ({
      state,
      patch,
      placeRef: state.place === CUSTOM ? { lat: state.lat, lon: state.lon } : { place: state.place },
      years: { start: state.start, end: state.end },
    }),
    [state, patch],
  )
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

/** Read and update the shared app state. */
export function useApp(): Ctx {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used inside <AppStateProvider>')
  return ctx
}
