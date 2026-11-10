/** Pure functions that turn API data into ECharts options (easy to unit-test; no React in here). */

import type { EChartsCoreOption } from 'echarts/core'
import type {
  CorrelationsResponse, FireTimeline, OverviewReady, RegionalRow, SeriesOk,
} from '../api/types'
import { fixed, MONTHS, signed } from '../lib/format'
import { C, FONT } from '../lib/palette'

type Num = number | null

const BASE = {
  backgroundColor: 'transparent',
  textStyle: { fontFamily: FONT, color: C.ink2 },
  animationDuration: 450,
  animationEasing: 'cubicOut',
} as const

const axisLabel = { color: C.muted, fontFamily: FONT }
const tooltipBase = {
  backgroundColor: C.surface2, borderColor: C.lineStrong, borderWidth: 1, padding: [8, 12],
  textStyle: { color: C.ink, fontFamily: FONT, fontSize: 13 },
}
const legendBase = { top: 0, left: 0, itemWidth: 16, itemHeight: 8, textStyle: { color: C.ink2, fontSize: 12 } }

const pairs = (x: (string | number)[], y: Num[]): [string | number, Num][] => y.map((v, i) => [x[i]!, v])
const gap = (hi: Num[], lo: Num[]): Num[] => hi.map((h, i) => (h !== null && lo[i] !== null && lo[i] !== undefined ? h - lo[i]! : null))

/** Monthly record, 12-month average, Sen trend and its 95% uncertainty wedge. */
export function trendOption(s: SeriesOk, anomalies: boolean): EChartsCoreOption {
  const m = s.monthly
  const low = anomalies ? m.wedgeLowAnomaly : m.wedgeLow
  const high = anomalies ? m.wedgeHighAnomaly : m.wedgeHigh
  const v = s.variable
  const shown = ['Monthly', '12-month average', 'Trend (Sen slope)']
  const jump = s.trend.jump
  return {
    ...BASE,
    grid: { left: 8, right: 96, top: 64, bottom: 28, containLabel: true },
    legend: { ...legendBase, data: ['Monthly', '12-month average', 'Trend (Sen slope)', '95% range of the trend'] },
    tooltip: {
      ...tooltipBase, trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: C.lineStrong } },
      formatter: (raw: unknown) => {
        const ps = (raw as { seriesName: string; value: [string, Num]; marker: string; axisValueLabel: string }[])
          .filter((p) => shown.includes(p.seriesName) && p.value[1] !== null)
        if (!ps.length) return ''
        return `<b>${ps[0]!.axisValueLabel}</b><br/>` +
          ps.map((p) => `${p.marker} ${p.seriesName}: <b>${fixed(p.value[1], v.decimals)}</b> ${v.unit}`).join('<br/>')
      },
    },
    dataZoom: [{ type: 'inside', filterMode: 'none' }],
    xAxis: { type: 'time', axisLine: { lineStyle: { color: C.lineStrong } }, axisLabel, splitLine: { show: false } },
    yAxis: {
      type: 'value', scale: !anomalies, name: anomalies ? `Anomaly (${v.unit})` : v.unit,
      nameTextStyle: { color: C.muted, align: 'left' }, axisLabel, splitLine: { lineStyle: { color: C.line } },
    },
    series: [
      { name: 'band-base', type: 'line', stack: 'band', data: pairs(m.dates, low), symbol: 'none', silent: true,
        lineStyle: { opacity: 0 }, z: 1 },
      { name: '95% range of the trend', type: 'line', stack: 'band', data: pairs(m.dates, gap(high, low)), symbol: 'none',
        silent: true, lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(217,89,38,0.16)' }, z: 1 },
      { name: 'Monthly', type: 'line', data: pairs(m.dates, anomalies ? m.anomalies : m.values), showSymbol: false,
        lineStyle: { width: 1, color: C.muted, opacity: 0.75 }, itemStyle: { color: C.muted }, z: 2 },
      { name: '12-month average', type: 'line', data: pairs(m.dates, anomalies ? m.smoothAnomaly : m.smooth),
        showSymbol: false, smooth: 0.2, lineStyle: { width: 2, color: C.blue }, itemStyle: { color: C.blue }, z: 3 },
      { name: 'Trend (Sen slope)', type: 'line', data: pairs(m.dates, anomalies ? m.trendAnomaly : m.trend), showSymbol: false,
        lineStyle: { width: 2.5, color: C.orange }, itemStyle: { color: C.orange }, z: 4,
        endLabel: { show: true, color: C.orange, fontSize: 12, formatter: () => `${signed(s.trend.perDecade, v.decimals)}/decade` },
        markLine: s.trend.jump.suspicious && jump.year
          ? { silent: true, symbol: 'none', lineStyle: { color: C.ink2, type: 'dotted', width: 1 },
              label: { formatter: `possible data jump, ${jump.year}`, color: C.ink2, position: 'insideEndTop' },
              data: [{ xAxis: `${jump.year}-01` }] }
          : undefined },
    ],
  }
}

/** One dot per year (what the statistical test uses) with the trend and its wedge. */
export function annualOption(s: SeriesOk): EChartsCoreOption {
  const a = s.annual
  const v = s.variable
  const years = a.years.map(String)
  const vals = a.values
  const finite = vals.map((x, i) => [x, i] as const).filter((p): p is [number, number] => p[0] !== null)
  const hi = finite.reduce((b, p) => (p[0] > b[0] ? p : b), finite[0]!)
  const lo = finite.reduce((b, p) => (p[0] < b[0] ? p : b), finite[0]!)
  const mark = (p: [number, number], word: string) => ({
    coord: [years[p[1]], p[0]], symbolSize: 1, label: { show: true, formatter: `${word}: ${years[p[1]]}`, color: C.ink2, fontSize: 12,
      position: word === 'highest' ? 'top' : 'bottom' },
  })
  return {
    ...BASE,
    grid: { left: 8, right: 16, top: 64, bottom: 24, containLabel: true },
    legend: { ...legendBase, data: ['Yearly average', 'Trend (Sen slope)', '95% range of the trend'] },
    tooltip: { ...tooltipBase, trigger: 'axis',
      formatter: (raw: unknown) => {
        const p = (raw as { seriesName: string; value: Num; axisValue: string; marker: string }[]).find((x) => x.seriesName === 'Yearly average')
        return p && p.value !== null ? `<b>${p.axisValue}</b><br/>${p.marker} ${fixed(p.value, v.decimals)} ${v.unit}` : ''
      } },
    xAxis: { type: 'category', data: years, boundaryGap: false, axisLine: { lineStyle: { color: C.lineStrong } },
      axisLabel: { ...axisLabel, interval: 4 } },
    yAxis: { type: 'value', scale: true, name: v.unit, nameTextStyle: { color: C.muted, align: 'left' }, axisLabel,
      splitLine: { lineStyle: { color: C.line } } },
    series: [
      { name: 'band-base', type: 'line', stack: 'band', data: a.wedgeLow, symbol: 'none', silent: true, lineStyle: { opacity: 0 } },
      { name: '95% range of the trend', type: 'line', stack: 'band', data: gap(a.wedgeHigh, a.wedgeLow), symbol: 'none', silent: true,
        lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(217,89,38,0.16)' } },
      { name: 'Yearly average', type: 'line', data: vals, symbol: 'circle', symbolSize: 8,
        lineStyle: { width: 1, color: C.lineStrong }, itemStyle: { color: C.blue, borderColor: C.surface, borderWidth: 2 },
        markPoint: { silent: true, data: [mark(hi, 'highest'), mark(lo, 'lowest')] } },
      { name: 'Trend (Sen slope)', type: 'line', data: a.trend, showSymbol: false, lineStyle: { width: 2.5, color: C.orange },
        itemStyle: { color: C.orange } },
    ],
  }
}

/** Rate of change for each calendar month; solid bars are significant. */
export function seasonalOption(s: SeriesOk): EChartsCoreOption {
  const v = s.variable
  const data = s.seasonal.map((r) => ({
    value: r.perDecade,
    itemStyle: { color: (r.perDecade ?? 0) >= 0 ? C.rise : C.fall, opacity: r.p !== null && r.p < 0.05 ? 1 : 0.35, borderRadius: 4 },
  }))
  return {
    ...BASE,
    grid: { left: 8, right: 8, top: 16, bottom: 24, containLabel: true },
    tooltip: { ...tooltipBase, trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(255,255,255,0.04)' } },
      formatter: (raw: unknown) => {
        const p = (raw as { dataIndex: number }[])[0]
        const r = s.seasonal[p!.dataIndex]!
        return `<b>${MONTHS[r.month - 1]}</b><br/>${signed(r.perDecade, v.decimals)} ${v.unit} per decade<br/>p = ${r.p === null ? 'n/a' : r.p.toFixed(3)}`
      } },
    xAxis: { type: 'category', data: MONTHS, axisLine: { lineStyle: { color: C.lineStrong } }, axisLabel, axisTick: { show: false } },
    yAxis: { type: 'value', name: `${v.unit} per decade`, nameTextStyle: { color: C.muted, align: 'left' }, axisLabel,
      splitLine: { lineStyle: { color: C.line } } },
    series: [{ type: 'bar', data, barWidth: '60%' }],
  }
}

/** Actual soil wetness against what each model predicted for the same dates. */
export function forecastOption(o: OverviewReady): EChartsCoreOption {
  const b = o.backtest
  const line = (name: string, y: Num[], color: string, width: number, type: 'solid' | 'dashed' | 'dotted' = 'solid') => ({
    name, type: 'line' as const, data: pairs(b.targetDates, y), showSymbol: false, lineStyle: { width, color, type },
    itemStyle: { color },
  })
  return {
    ...BASE,
    grid: { left: 8, right: 16, top: 64, bottom: 28, containLabel: true },
    legend: { ...legendBase, data: ['Actual', 'Persistence', 'ARIMA', 'XGBoost'] },
    tooltip: { ...tooltipBase, trigger: 'axis' },
    dataZoom: [{ type: 'inside', filterMode: 'none' }],
    xAxis: { type: 'time', axisLine: { lineStyle: { color: C.lineStrong } }, axisLabel, splitLine: { show: false } },
    yAxis: { type: 'value', scale: true, name: 'wetness (0–1)', nameTextStyle: { color: C.muted, align: 'left' }, axisLabel,
      splitLine: { lineStyle: { color: C.line } } },
    series: [
      line('Actual', b.actual, C.ink, 3),
      line('Persistence', b.Persistence, C.muted, 1.5, 'dashed'),
      line('ARIMA', b.ARIMA, C.blue, 2),
      line('XGBoost', b.XGBoost, C.orange, 2),
    ],
  }
}

/** Heatmap of how every pair of variables moves together. */
export function correlationOption(c: CorrelationsResponse): EChartsCoreOption {
  const data: [number, number, Num][] = []
  c.matrix.forEach((row, y) => row.forEach((val, x) => data.push([x, y, val])))
  return {
    ...BASE,
    grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
    tooltip: { ...tooltipBase, formatter: (raw: unknown) => {
      const p = raw as { value: [number, number, Num] }
      return `${c.names[p.value[1]]} vs ${c.names[p.value[0]]}<br/>link strength <b>${p.value[2] === null ? 'n/a' : signed(p.value[2], 2)}</b>`
    } },
    xAxis: { type: 'category', data: c.names, axisLabel: { ...axisLabel, rotate: 45, interval: 0, fontSize: 11 }, splitArea: { show: false },
      axisLine: { show: false } },
    yAxis: { type: 'category', data: c.names, inverse: true, axisLabel: { ...axisLabel, color: C.ink2, interval: 0, fontSize: 11 }, axisLine: { show: false } },
    visualMap: { min: -1, max: 1, calculable: false, right: 0, top: 'center', itemHeight: 140, itemWidth: 10, text: ['+1', '−1'],
      textStyle: { color: C.ink2 }, inRange: { color: [C.fall, C.neutral, C.rise] } },
    series: [{ type: 'heatmap', data, itemStyle: { borderColor: C.surface, borderWidth: 1, borderRadius: 2 },
      emphasis: { itemStyle: { borderColor: C.ink, borderWidth: 1 } } }],
  }
}

/** The same variable at every place, sorted from most-falling to most-rising. */
export function rankedBarsOption(rows: RegionalRow[], unit: string, decimals: number): EChartsCoreOption {
  const sorted = [...rows].sort((a, b) => a.perDecade - b.perDecade)
  return {
    ...BASE,
    grid: { left: 8, right: 24, top: 8, bottom: 24, containLabel: true },
    tooltip: { ...tooltipBase, trigger: 'item', formatter: (raw: unknown) => {
      const r = sorted[(raw as { dataIndex: number }).dataIndex]!
      return `<b>${r.name}</b><br/>${signed(r.perDecade, decimals)} ${unit} per decade<br/>p = ${r.p.toFixed(3)}${r.significant ? ' (significant)' : ''}`
    } },
    xAxis: { type: 'value', name: `${unit} per decade`, nameLocation: 'middle', nameGap: 28, nameTextStyle: { color: C.muted }, axisLabel,
      splitLine: { lineStyle: { color: C.line } } },
    yAxis: { type: 'category', data: sorted.map((r) => r.name), axisLabel: { color: C.ink2, fontSize: 12 }, axisTick: { show: false },
      axisLine: { lineStyle: { color: C.lineStrong } } },
    series: [{ type: 'bar', barWidth: '62%',
      data: sorted.map((r) => ({ value: r.perDecade,
        itemStyle: { color: r.perDecade >= 0 ? C.rise : C.fall, opacity: r.significant ? 1 : 0.35, borderRadius: r.perDecade >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4] } })) }],
  }
}

/** Burned area over time for the three fire models, with a marker at the current time. */
export function timelineOption(t: FireTimeline, hour: number): EChartsCoreOption {
  const line = (name: string, y: number[], color: string, type: 'solid' | 'dashed' | 'dotted' = 'solid') => ({
    name, type: 'line' as const, data: t.hours.map((h, i) => [h, y[i]]), showSymbol: false, lineStyle: { width: 2, color, type },
    itemStyle: { color }, smooth: 0.2,
  })
  return {
    ...BASE,
    grid: { left: 8, right: 16, top: 64, bottom: 28, containLabel: true },
    legend: { ...legendBase, data: ['Deterministic', 'Probabilistic (≥50%)', 'Particle flow'] },
    tooltip: { ...tooltipBase, trigger: 'axis', valueFormatter: (v: unknown) => `${fixed(Number(v), 1)} ha` },
    xAxis: { type: 'value', min: 0, max: 12, name: 'hours since ignition', nameLocation: 'middle', nameGap: 28, nameTextStyle: { color: C.muted }, axisLabel,
      splitLine: { show: false }, axisLine: { lineStyle: { color: C.lineStrong } } },
    yAxis: { type: 'value', name: 'burned area (ha)', nameTextStyle: { color: C.muted, align: 'left' }, axisLabel, splitLine: { lineStyle: { color: C.line } } },
    series: [
      { ...line('Deterministic', t.detHa, C.blue),
        markLine: { silent: true, symbol: 'none', lineStyle: { color: C.ink2, type: 'dashed', width: 1 }, label: { show: false }, data: [{ xAxis: hour }] } },
      line('Probabilistic (≥50%)', t.probHa, C.orange),
      line('Particle flow', t.partHa, C.aqua, 'dashed'),
    ],
  }
}
