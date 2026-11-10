/** Risk Lab: soil-wetness forecasting (ARIMA, XGBoost) and wildfire simulation (three models). */

import { lazy, Suspense } from 'react'
import { api } from '../../api/endpoints'
import { Badge, Card, ErrorBox, Skeleton, Tabs, tierTone } from '../../components/ui'
import { useAsync } from '../../hooks'
import { useApp, type RiskTab } from '../../state'
import { Forecast } from './Forecast'
import { History } from './History'

const Fire = lazy(() => import('./Fire'))

/** Risk Lab: forecast, fire simulator and history tabs. */
export default function Risk() {
  const { state, patch } = useApp()
  const info = useAsync(() => api.riskRegions(), [])

  if (info.error) return <ErrorBox error={info.error} />
  if (!info.data) return <Skeleton height={300} />
  const d = info.data

  return (
    <div className="fade-in">
      <div className="hero">
        <div className="eyebrow">Risk Lab</div>
        <h1>Drought forecast. Fire spread.</h1>
        <p className="lead">Predict how dry the soil will be, then watch how a wildfire would move across the land.</p>
      </div>

      <Card>
        <div className="grid cols-2" style={{ gap: 32 }}>
          <div className="stack">
            <span className="eyebrow">What exactly is predicted</span>
            <h3 style={{ fontSize: 20 }}>{d.target.label}</h3>
            <p className="note">
              A single fixed target (<code>{d.target.code}</code>, a 0 to 1 fraction) predicted {state.horizon} days ahead. Every forecasting model
              answers this same question, so they can be compared fairly.
            </p>
            <label className="field" style={{ maxWidth: 340 }}>Region
              <select value={state.region} onChange={(e) => patch({ region: e.target.value })}>
                {d.regions.map((r) => <option key={r.name}>{r.name}</option>)}
              </select>
            </label>
          </div>
          <div className="stack">
            <span className="eyebrow">Models, by priority</span>
            <div className="row">
              {Object.entries(d.forecastTiers).map(([m, t]) => <span key={m}><Badge label={t.replace(' (not implemented)', '')} tone={tierTone(t)} /> {m}</span>)}
            </div>
            <div className="row">
              {d.fireModels.map((m) => <span key={m.id}><Badge label={m.tier} tone={tierTone(m.tier)} /> {m.name}</span>)}
            </div>
          </div>
        </div>
      </Card>

      <div style={{ margin: '24px 0' }}>
        <Tabs<RiskTab> label="Risk Lab section" value={state.riskTab} onChange={(riskTab) => patch({ riskTab })}
          options={[{ id: 'forecast', label: '1 · Forecast' }, { id: 'fire', label: '2 · Fire simulator' }, { id: 'history', label: '3 · History' }]} />
      </div>
      {state.riskTab === 'forecast' && <Forecast info={d} />}
      {state.riskTab === 'fire' && <Suspense fallback={<Skeleton height={560} />}><Fire info={d} /></Suspense>}
      {state.riskTab === 'history' && <History />}
    </div>
  )
}
