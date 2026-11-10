/** One typed function per API endpoint. */

import { get, post } from './client'
import type {
  AnswerResponse, CorrelationsResponse, EventItem, FireRequest, FireResponse, HistoryResponse, Meta,
  OverviewResponse, RegionalResponse, RiskRegionsResponse, ScanResponse, SeriesResponse,
} from './types'

export type PlaceRef = { place: string } | { lat: number; lon: number }
export interface YearSpan {
  start: number
  end: number
}

const placeQuery = (r: PlaceRef): string =>
  'place' in r ? `place=${encodeURIComponent(r.place)}` : `lat=${r.lat}&lon=${r.lon}`
const windowQuery = (w: YearSpan): string => `start=${w.start}&end=${w.end}`

export const trendsUrl = {
  scan: (r: PlaceRef, w: YearSpan) => `/api/trends/scan?${placeQuery(r)}&${windowQuery(w)}`,
  series: (r: PlaceRef, w: YearSpan, code: string) => `/api/trends/series?${placeQuery(r)}&${windowQuery(w)}&code=${code}`,
  answer: (r: PlaceRef, w: YearSpan, q: string) => `/api/trends/answer?${placeQuery(r)}&${windowQuery(w)}&question=${q}`,
  regional: (r: PlaceRef, w: YearSpan, code: string) => `/api/trends/regional?${placeQuery(r)}&${windowQuery(w)}&code=${code}`,
  correlations: (r: PlaceRef, w: YearSpan) => `/api/trends/correlations?${placeQuery(r)}&${windowQuery(w)}`,
  report: (r: PlaceRef, w: YearSpan) => `/api/trends/report?${placeQuery(r)}&${windowQuery(w)}`,
}

export const api = {
  meta: () => get<Meta>('/api/meta'),
  scan: (r: PlaceRef, w: YearSpan) => get<ScanResponse>(trendsUrl.scan(r, w)),
  series: (r: PlaceRef, w: YearSpan, code: string) => get<SeriesResponse>(trendsUrl.series(r, w, code)),
  answer: (r: PlaceRef, w: YearSpan, q: string) => get<AnswerResponse>(trendsUrl.answer(r, w, q)),
  regional: (r: PlaceRef, w: YearSpan, code: string) => get<RegionalResponse>(trendsUrl.regional(r, w, code)),
  correlations: (r: PlaceRef, w: YearSpan) => get<CorrelationsResponse>(trendsUrl.correlations(r, w)),
  events: () => get<{ events: EventItem[] }>('/api/trends/events'),

  riskRegions: () => get<RiskRegionsResponse>('/api/risk/regions'),
  overview: (region: string, horizon: number) =>
    get<OverviewResponse>(`/api/risk/overview?region=${encodeURIComponent(region)}&horizon=${horizon}`, { fresh: true }),
  fire: (req: FireRequest) => post<FireResponse>('/api/risk/fire', req),
  saveRun: (body: Record<string, unknown>) => post<{ id: number }>('/api/risk/history', body),
  saveBenchmark: (region: string, horizon: number) => post<{ saved: number }>('/api/risk/benchmarks', { region, horizon }),
  history: () => get<HistoryResponse>('/api/risk/history', { fresh: true }),
}
