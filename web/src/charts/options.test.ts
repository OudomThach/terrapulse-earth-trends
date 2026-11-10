import { describe, expect, it } from 'vitest'
import type { CorrelationsResponse, FireTimeline, RegionalRow, SeriesOk } from '../api/types'
import { annualOption, correlationOption, rankedBarsOption, seasonalOption, timelineOption, trendOption } from './options'

type Opt = Record<string, unknown> & { series: Record<string, unknown>[] }

function fakeSeries(suspicious: boolean): SeriesOk {
  const dates = ['1990-01', '1990-02', '1990-03']
  const arr = (a: number, b: number, c: number) => [a, b, c]
  return {
    usable: true,
    place: { name: 'X', lat: 0, lon: 0, biome: 'b', blurb: '' }, window: { start: 1990, end: 1992 },
    variable: { code: 'T2M', name: 'Air temperature', unit: '°C', group: 'Temperature', decimals: 2, definition: '', risingMeans: '' },
    trend: { usable: true, perDecade: 0.5, jump: { year: suspicious ? 1991 : null, suspicious } } as unknown as SeriesOk['trend'],
    monthly: {
      dates, values: arr(1, 2, 3), anomalies: arr(-1, 0, 1), smooth: arr(1, 2, 3), smoothAnomaly: arr(-1, 0, 1), trend: arr(1, 2, 3),
      trendAnomaly: arr(-1, 0, 1), wedgeLow: arr(0.5, 1.5, 2.5), wedgeHigh: arr(1.5, 2.5, 3.5), wedgeLowAnomaly: arr(-1.5, -0.5, 0.5),
      wedgeHighAnomaly: arr(-0.5, 0.5, 1.5),
    },
    annual: { years: [1990, 1991, 1992], values: [1, 3, 2], trend: [1, 2, 3], wedgeLow: [0, 1, 2], wedgeHigh: [2, 3, 4] },
    seasonal: Array.from({ length: 12 }, (_, i) => ({ month: i + 1, perDecade: i % 2 ? -0.2 : 0.3, p: i === 0 ? 0.01 : 0.5 })),
    verdict: { tone: 'sig', headline: '', body: '', label: '' }, jumpWarning: null, yearsToSignificance: null, probabilityText: '',
  }
}

describe('trendOption', () => {
  it('stacks a transparent base and a shaded wedge so the band follows the trend', () => {
    const o = trendOption(fakeSeries(false), false) as Opt
    expect(o.series.map((s) => s.name)).toEqual(['band-base', '95% range of the trend', 'Monthly', '12-month average', 'Trend (Sen slope)'])
    const base = (o.series[0]!.data as [string, number][]).map((p) => p[1])
    const width = (o.series[1]!.data as [string, number][]).map((p) => p[1])
    expect(base).toEqual([0.5, 1.5, 2.5])
    expect(width).toEqual([1, 1, 1]) // high - low
    expect(o.series[0]!.stack).toBe(o.series[1]!.stack)
  })
  it('switches between real values and anomalies', () => {
    const vals = trendOption(fakeSeries(false), false) as Opt
    const anom = trendOption(fakeSeries(false), true) as Opt
    expect((vals.series[2]!.data as [string, number][])[0]![1]).toBe(1)
    expect((anom.series[2]!.data as [string, number][])[0]![1]).toBe(-1)
  })
  it('only marks a data jump when the detective flagged one', () => {
    const plain = trendOption(fakeSeries(false), true) as Opt
    const jump = trendOption(fakeSeries(true), true) as Opt
    expect(plain.series[4]!.markLine).toBeUndefined()
    expect(JSON.stringify(jump.series[4]!.markLine)).toContain('1991-01')
  })
})

describe('annualOption and seasonalOption', () => {
  it('annotates the highest and lowest years', () => {
    const o = annualOption(fakeSeries(false)) as Opt
    const mark = JSON.stringify((o.series[2]!.markPoint as { data: unknown }).data)
    expect(mark).toContain('highest: 1991')
    expect(mark).toContain('lowest: 1990')
  })
  it('draws significant months solid and the rest faded, coloured by direction', () => {
    const o = seasonalOption(fakeSeries(false)) as Opt
    const data = o.series[0]!.data as { value: number; itemStyle: { opacity: number; color: string } }[]
    expect(data).toHaveLength(12)
    expect(data[0]!.itemStyle.opacity).toBe(1)
    expect(data[1]!.itemStyle.opacity).toBeLessThan(1)
    expect(data[0]!.itemStyle.color).not.toBe(data[1]!.itemStyle.color) // rising vs falling
  })
})

describe('other charts', () => {
  it('sorts the ranked bars from most falling to most rising and fades non-significant places', () => {
    const rows: RegionalRow[] = [
      { name: 'A', lat: 0, lon: 0, biome: '', perDecade: 0.5, p: 0.01, q: 0.02, significant: true, jump: false },
      { name: 'B', lat: 0, lon: 0, biome: '', perDecade: -0.2, p: 0.3, q: 0.4, significant: false, jump: false },
    ]
    const o = rankedBarsOption(rows, '°C', 2) as unknown as { yAxis: { data: string[] }; series: { data: { itemStyle: { opacity: number } }[] }[] }
    expect(o.yAxis.data).toEqual(['B', 'A'])
    expect(o.series[0]!.data.map((d) => d.itemStyle.opacity)).toEqual([0.35, 1])
  })
  it('lays the correlation heatmap out cell by cell', () => {
    const c: CorrelationsResponse = { codes: ['a', 'b'], names: ['A', 'B'], matrix: [[1, 0.5], [0.5, 1]], links: [], story: [] }
    const o = correlationOption(c) as Opt
    expect((o.series[0]!.data as unknown[]).length).toBe(4)
  })
  it('places the playhead on the burned-area timeline', () => {
    const t: FireTimeline = { hours: [0, 0.25], detHa: [0, 1], probHa: [0, 1], partHa: [0, 1], frontKm: [0, 0], patches: [0, 1], iouDetProb: [1, 1], iouDetPart: [1, 1], iouProbPart: [1, 1] }
    const o = timelineOption(t, 0.25) as Opt
    expect(o.series).toHaveLength(3)
    expect(JSON.stringify(o.series[0]!.markLine)).toContain('0.25')
  })
})
