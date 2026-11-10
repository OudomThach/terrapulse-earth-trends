/** Types that mirror the JSON returned by the TerraPulse API (see server/serialize.py). */

export type Direction = 'rising' | 'falling' | 'flat'
export type EvidenceLabel = 'Strong evidence' | 'Significant' | 'Weak hint' | 'No clear trend'
export type Tone = 'strong' | 'sig' | 'weak' | 'none' | 'warn'

export interface PlaceInfo {
  name: string
  lat: number
  lon: number
  biome: string
  blurb: string
}

export interface VariableInfo {
  code: string
  name: string
  unit: string
  group: string
  definition: string
  risingMeans: string
  decimals: number
  since: number | null
}

export interface QuestionInfo {
  id: string
  text: string
  why: string
  clues: string[]
}

export interface FeedbackItem {
  id: string
  instructor: string
  response: string
  status: string
  where: string
}

export interface Requirement {
  item: string
  status: 'done' | 'partial' | 'optional' | 'todo'
  where: string
}

export interface Meta {
  version: string
  years: { first: number; last: number }
  places: PlaceInfo[]
  groups: string[]
  variables: VariableInfo[]
  questions: QuestionInfo[]
  feedback: FeedbackItem[]
  requirements: Requirement[]
}

// ---------------------------------------------------------------------------------- trends
interface TrendBase {
  code: string
  name: string
  unit: string
  group: string
  decimals: number
}

export interface TrendUnusable extends TrendBase {
  usable: false
  reason: string
}

export interface TrendOk extends TrendBase {
  usable: true
  reason: string
  perDecade: number
  ciLow: number
  ciHigh: number
  p: number
  q: number | null
  z: number
  tau: number
  label: EvidenceLabel
  dots: string
  direction: Direction
  totalChange: number
  pctChange: number | null
  spanYears: number
  mean: number
  lag1: number
  inflation: number
  rateText: string
  ols: { perDecade: number; low: number; high: number; r2: number; p: number }
  jump: { year: number | null; p: number; before: number | null; after: number | null; fitRatio: number | null; suspicious: boolean }
  annual: { years: number[]; values: (number | null)[] }
}

export type Trend = TrendOk | TrendUnusable

export interface ScanResponse {
  place: PlaceInfo
  window: { start: number; end: number }
  summary: {
    tested: number
    available: number
    significant: number
    jumps: number
    strongest: { code: string; name: string; rateText: string; direction: Direction } | null
  }
  results: Trend[]
}

type Series = (number | null)[]

export interface SeriesOk {
  usable: true
  place: PlaceInfo
  window: { start: number; end: number }
  variable: { code: string; name: string; unit: string; group: string; decimals: number; definition: string; risingMeans: string }
  trend: TrendOk
  monthly: {
    dates: string[]
    values: Series
    anomalies: Series
    smooth: Series
    smoothAnomaly: Series
    trend: Series
    trendAnomaly: Series
    wedgeLow: Series
    wedgeHigh: Series
    wedgeLowAnomaly: Series
    wedgeHighAnomaly: Series
  }
  annual: { years: number[]; values: Series; trend: Series; wedgeLow: Series; wedgeHigh: Series }
  seasonal: { month: number; perDecade: number | null; p: number | null }[]
  verdict: { tone: Tone; headline: string; body: string; label: string }
  jumpWarning: string | null
  yearsToSignificance: number | null
  probabilityText: string
}

export interface SeriesUnusable {
  usable: false
  reason: string
  trend: TrendUnusable
}

export type SeriesResponse = SeriesOk | SeriesUnusable

export interface AnswerResponse {
  id: string
  text: string
  why: string
  outcome: 'up' | 'down' | 'mixed' | 'none' | 'unknown'
  headline: string
  body: string
  tone: Tone
  codes: string[]
}

export interface RegionalRow {
  name: string
  lat: number
  lon: number
  biome: string
  perDecade: number
  p: number
  q: number
  significant: boolean
  jump: boolean
}

export interface RegionalResponse {
  code: string
  rows: RegionalRow[]
  finding: { kind: 'opposite' | 'one-way' | 'none'; headline: string; body: string; rising?: number; falling?: number; none?: number }
}

export interface CorrelationLink {
  a: string
  b: string
  aName: string
  bName: string
  rho: number
  note: string | null
  matches: boolean | null
}

export interface CorrelationsResponse {
  codes: string[]
  names: string[]
  matrix: (number | null)[][]
  links: CorrelationLink[]
  story: { title: string; text: string; codes: string[] }[]
}

export interface EventItem {
  title: string
  category: string
  date: string
  lat: number
  lon: number
}

// ---------------------------------------------------------------------------------- risk lab
export interface RiskRegion {
  name: string
  lat: number
  lon: number
  reliefM: number
}

export interface FireModelInfo {
  id: 'deterministic' | 'probabilistic' | 'particle'
  name: string
  tier: string
  summary: string
}

export interface RiskRegionsResponse {
  regions: RiskRegion[]
  target: { code: string; label: string }
  defaultHorizon: number
  fireModels: FireModelInfo[]
  forecastTiers: Record<string, string>
}

export interface OverviewReady {
  status: 'ready'
  region: string
  horizon: number
  target: { code: string; label: string }
  dataSource: string
  nOrigins: number
  latest: { date: string; value: number }
  forecastDate: string
  forecasts: Record<string, number | null>
  models: { name: string; tier: string; mse: number; rmse: number; r2: number | null; best: boolean }[]
  backtest: { targetDates: string[]; actual: Series; Persistence: Series; ARIMA: Series; XGBoost: Series }
  history: { dates: string[]; values: Series }
}

export type OverviewResponse = OverviewReady | { status: 'computing'; region: string; horizon: number }

export interface FireRequest {
  region: string
  row: number
  col: number
  wind_kmh: number
  wind_toward_deg: number
  wetness_source: 'forecast' | 'manual'
  forecast_model: 'Persistence' | 'ARIMA' | 'XGBoost'
  manual_wetness: number
  horizon: number
  n_runs: number
}

export interface FireTimeline {
  hours: number[]
  detHa: number[]
  probHa: number[]
  partHa: number[]
  frontKm: number[]
  patches: number[]
  iouDetProb: number[]
  iouDetPart: number[]
  iouProbPart: number[]
}

export interface FireResponse {
  region: string
  grid: { rows: number; cols: number; cellM: number }
  ignition: { row: number; col: number }
  wind: { kmh: number; towardDeg: number }
  wetness: number
  wetnessSource: string
  dryness: number
  dem: (number | null)[]
  terrainSource: string
  deterministic: (number | null)[]
  particle: (number | null)[]
  ensemble: { runs: number; quantumMin: number; never: number; data: string }
  timeline: FireTimeline
}

export interface SavedSimulation {
  id: number
  created_at: string
  region: string
  forecast_model: string | null
  forecast_wetness: number | null
  dryness: number
  wind_speed_ms: number
  wind_toward_deg: number
  hours: number
  det_burned_ha: number
  prob_burned_ha: number | null
  iou: number | null
}

export interface SavedBenchmark {
  id: number
  created_at: string
  region: string
  horizon_days: number
  model: string
  mse: number
  rmse: number
  r2: number | null
}

export interface HistoryResponse {
  simulations: SavedSimulation[]
  benchmarks: SavedBenchmark[]
}
