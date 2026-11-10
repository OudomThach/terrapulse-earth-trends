/** Risk Lab > Forecast: ARIMA, XGBoost and a persistence reference, all predicting the same fixed target. */

import { useMemo, useState } from 'react'
import { api } from '../../api/endpoints'
import type { OverviewReady, RiskRegionsResponse } from '../../api/types'
import { EChart } from '../../charts/EChart'
import { forecastOption } from '../../charts/options'
import { Badge, Banner, Card, ErrorBox, Kpi, KpiRow, Section, Skeleton, tierTone } from '../../components/ui'
import { Slider } from '../../components/Slider'
import { useAsync, useDebounced, useInterval } from '../../hooks'
import { fixed } from '../../lib/format'
import { useApp } from '../../state'

/** Soil-wetness forecast 14 days ahead: ARIMA, XGBoost and persistence compared by a rolling backtest. */
export function Forecast({ info }: { info: RiskRegionsResponse }) {
  const { state, patch } = useApp()
  const [horizon, setHorizon] = useState(state.horizon)
  const settled = useDebounced(horizon, 300)
  const [tick, setTick] = useState(0)
  const [note, setNote] = useState<string | null>(null)
  const ov = useAsync(() => api.overview(state.region, settled), [state.region, settled, tick])
  const computing = ov.data?.status === 'computing'
  useInterval(() => setTick((t) => t + 1), 2500, computing)

  const ready: OverviewReady | undefined = ov.data?.status === 'ready' ? ov.data : undefined
  const option = useMemo(() => (ready ? forecastOption(ready) : null), [ready])

  const save = async () => {
    try {
      const r = await api.saveBenchmark(state.region, settled)
      setNote(`Saved ${r.saved} model scores to the history.`)
    } catch (e) {
      setNote((e as Error).message)
    }
  }

  return (
    <div className="fade-in">
      <div className="grid cols-2" style={{ alignItems: 'end' }}>
        <Slider label="Forecast horizon" value={horizon} min={7} max={28} format={(v) => `${v} days`}
          onChange={(v) => { setHorizon(v); patch({ horizon: v }) }} />
        <p className="note">Every model predicts <b>{info.target.label}</b>, exactly this many days after the latest observation.</p>
      </div>

      {ov.error && <ErrorBox error={ov.error} />}
      {computing && (
        <Banner eyebrow="Working" headline={`Backtesting ${settled}-day forecasts`} tone="none">
          ARIMA is re-fitted at 52 start dates, which takes about 40 seconds the first time. Results are then saved on disk, so every
          later visit is instant.
        </Banner>
      )}
      {!ov.data && !ov.error && <Skeleton height={380} />}
      {(computing || (!ready && ov.data)) && !ready && <Skeleton height={320} />}

      {ready && (
        <div style={{ opacity: ov.loading ? 0.6 : 1, transition: 'opacity .2s' }}>
          <KpiRow>
            <Kpi label={`Soil wetness now (${ready.latest.date})`} value={fixed(ready.latest.value, 3)} sub={ready.target.label} />
            {ready.models.map((m) => (
              <Kpi key={m.name} label={`${m.name} forecast · ${ready.forecastDate}`} value={fixed(ready.forecasts[m.name], 3)}
                sub={<><Badge label={m.tier} tone={tierTone(m.tier)} /> {m.best && <b style={{ color: 'var(--accent)' }}>lowest error</b>}</>} />
            ))}
          </KpiRow>

          <Section title="Experiment 1: which model predicts best?"
            sub={`Each model forecasts ${ready.horizon} days ahead from ${ready.nOrigins} weekly start dates over the past year and is re-trained each time. Lower error is better.`}
            action={<button className="btn small" onClick={save}>Save comparison to history</button>} />
          {note && <p className="note" role="status">{note}</p>}
          <div className="grid side">
            <Card className="tight">{option && <EChart option={option} height={380} label="Actual and forecast soil wetness" />}</Card>
            <Card className="tight">
              <table>
                <thead><tr><th>Model</th><th>MSE</th><th>RMSE</th><th>R²</th></tr></thead>
                <tbody>
                  {ready.models.map((m) => (
                    <tr key={m.name} style={m.best ? { background: 'rgba(63,212,162,.08)' } : undefined}>
                      <td><b>{m.name}</b> <Badge label={m.tier} tone={tierTone(m.tier)} /></td>
                      <td>{m.mse.toFixed(5)}</td><td>{m.rmse.toFixed(4)}</td><td>{m.r2 === null ? 'n/a' : m.r2.toFixed(3)}</td>
                    </tr>
                  ))}
                  <tr><td><b>LSTM</b> <Badge label="Optional" tone="optional" /></td><td colSpan={3} className="muted">not implemented (optional per the instructor)</td></tr>
                </tbody>
              </table>
              <p className="note" style={{ marginTop: 16 }}>
                Persistence ("it stays the same") is the reference every real model has to beat. Where soil changes slowly, nothing beats it.
                That is an honest result, not a bug.
              </p>
              <p className="note">Data: {ready.dataSource}</p>
            </Card>
          </div>
        </div>
      )}
    </div>
  )
}
