/** Stage 2: the full investigation of one variable (verdict, statistics, charts, caveats). */

import { useMemo, useState } from 'react'
import { api } from '../../api/endpoints'
import type { SeriesOk } from '../../api/types'
import { EChart } from '../../charts/EChart'
import { annualOption, seasonalOption, trendOption } from '../../charts/options'
import {
  Banner, Card, DataTable, ErrorBox, Kpi, KpiRow, RichText, Section, Skeleton, Tabs, Toggle,
} from '../../components/ui'
import { useAsync } from '../../hooks'
import { fixed, pText, signed } from '../../lib/format'
import { VariableSelect } from '../../components/VariableSelect'
import { useApp } from '../../state'

function Statistics({ s }: { s: SeriesOk }) {
  const t = s.trend
  const d = t.decimals
  const u = s.variable.unit
  const agree = (t.ols.p < 0.05) === (t.p < 0.05)
  const pct = t.pctChange !== null && Math.abs(t.pctChange) < 1e4 ? `, ${signed(t.pctChange, 0)}% of the average` : ''
  return (
    <KpiRow>
      <Kpi label="Rate of change" value={t.rateText} sub="Sen's slope: the median of all pairwise slopes" tone={t.direction === 'rising' ? 'rise' : 'fall'} />
      <Kpi label="Total change" value={`${signed(t.totalChange, d)} ${u}`} sub={`over ${t.spanYears.toFixed(0)} years${pct}`} />
      <Kpi label="95% confidence range" value={`${signed(t.ciLow, d)} to ${signed(t.ciHigh, d)}`} sub="per decade. If it spans zero, the trend is not proven" />
      <Kpi label="Chance it is luck" value={pText(t.p)} sub={s.probabilityText} />
      <Kpi label="Cross-check" value={`${signed(t.ols.perDecade, d)} per decade`}
        sub={`${agree ? 'Straight-line fit agrees' : 'Methods disagree: be careful'} (R² = ${t.ols.r2.toFixed(2)})`} />
      <Kpi label="Year-to-year memory" value={signed(t.lag1, 2)}
        sub={t.inflation > 1 ? 'Adjusted for it so persistence cannot fake a trend' : 'Low, so no adjustment needed'} />
    </KpiRow>
  )
}

/** Evidence stage: the evidence for one variable (trend line, confidence band, jump check, seasons). */
export function Evidence() {
  const { state, patch, placeRef, years } = useApp()
  const [anomalies, setAnomalies] = useState(true)
  const [table, setTable] = useState(false)
  const series = useAsync(() => api.series(placeRef, years, state.code), [JSON.stringify(placeRef), years.start, years.end, state.code])

  const s = series.data && series.data.usable ? series.data : undefined
  const trend = useMemo(() => (s ? trendOption(s, anomalies) : null), [s, anomalies])
  const annual = useMemo(() => (s ? annualOption(s) : null), [s])
  const seasonal = useMemo(() => (s ? seasonalOption(s) : null), [s])

  return (
    <div className="fade-in">
      <div style={{ maxWidth: 420, marginBottom: 16 }}>
        <VariableSelect label="Which clue are you testing?" value={state.code} onChange={(code) => patch({ code })} />
      </div>
      {series.error && <ErrorBox error={series.error} />}
      {!series.data && !series.error && <Skeleton height={420} />}
      {series.data && !series.data.usable && (
        <Banner headline="This clue cannot be tested here" tone="none">{series.data.reason}</Banner>
      )}
      {s && (
        <div className={series.loading ? 'dim' : ''} style={{ transition: 'opacity .2s', opacity: series.loading ? 0.6 : 1 }}>
          <Banner
            eyebrow={`${s.verdict.label} · ${s.trend.dots}${s.trend.jump.suspicious ? ' · read the caution below' : ''}`}
            headline={s.verdict.headline}
            tone={s.trend.jump.suspicious ? 'weak' : s.verdict.tone}
          >
            <RichText text={s.verdict.body} />
          </Banner>
          {s.jumpWarning && (
            <>
              <Banner eyebrow="Detective's caution" headline="Is this a real trend?" tone="warn"><RichText text={s.jumpWarning} /></Banner>
              {s.trend.jump.year !== null && s.trend.jump.year + 9 <= s.window.end
                ? <button className="btn primary" onClick={() => patch({ start: s.trend.jump.year! })}>Re-test from {s.trend.jump.year} onward</button>
                : <p className="note">Not enough years after the jump to re-test.</p>}
            </>
          )}
          <Statistics s={s} />

          <Section title="The full record" sub="Every month in the window, with the trend and how sure we are of it. Scroll to zoom, drag to pan."
            action={
              <Tabs label="Chart mode" value={anomalies ? 'anom' : 'vals'} onChange={(v) => setAnomalies(v === 'anom')}
                options={[{ id: 'anom', label: 'Seasons removed' }, { id: 'vals', label: 'Real values' }]} />
            } />
          <Card className="tight">{trend && <EChart option={trend} height={400} label={`Monthly ${s.variable.name} with trend`} />}</Card>
          <p className="note" style={{ marginTop: 8 }}>
            Grey: each month. Blue: 12-month average, which smooths out the seasons. Orange: the trend, with its 95% range shaded.
          </p>

          <div className="grid cols-2" style={{ marginTop: 8 }}>
            <div>
              <Section title="Year by year" sub="These yearly averages are what the statistical test actually uses." />
              <Card className="tight">{annual && <EChart option={annual} height={320} label="Yearly averages with trend" />}</Card>
            </div>
            <div>
              <Section title="Which seasons drive it?" sub="Rate of change for each calendar month on its own. Solid bars are significant." />
              <Card className="tight">{seasonal && <EChart option={seasonal} height={320} label="Trend by calendar month" />}</Card>
            </div>
          </div>

          <div className="grid cols-3" style={{ marginTop: 24 }}>
            <details>
              <summary>What is this variable?</summary>
              <div><b>{s.variable.name}</b> ({s.variable.unit}). {s.variable.definition}<br /><i>If it rises:</i> {s.variable.risingMeans}</div>
            </details>
            <details>
              <summary>How to read these charts</summary>
              <div>
                <b>Trend line</b>: the steady rate of change that best fits the data. <b>Orange band</b>: other trend lines that fit almost as
                well; if a flat line fits inside it, the trend is not proven. <b>p-value</b>: how often luck alone would draw a pattern this
                strong (below 0.05 is called significant). <b>Colour</b> shows direction, never good or bad.
              </div>
            </details>
            <div className="row" style={{ alignItems: 'flex-start' }}>
              <Toggle label="Show the data table" checked={table} onChange={setTable} />
            </div>
          </div>
          {table && (
            <div style={{ marginTop: 16 }}>
              <DataTable columns={['Year', `Yearly mean (${s.variable.unit})`, `Trend line (${s.variable.unit})`]}
                rows={s.annual.years.map((y, i) => [y, fixed(s.annual.values[i], s.variable.decimals + 1), fixed(s.annual.trend[i], s.variable.decimals + 1)])} />
            </div>
          )}
          {s.trend.p >= 0.05 && s.yearsToSignificance && (
            <Banner headline="What would it take?" tone="none">
              At the current rate and noise, about <b>{s.yearsToSignificance} more years</b> of data would turn this from "not proven" into
              significant. Short records often just need more time.
            </Banner>
          )}
        </div>
      )}
    </div>
  )
}
