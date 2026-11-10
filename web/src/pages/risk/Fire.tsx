/** Risk Lab > Fire simulator: three models on 3D terrain. The server computes arrival times once;
 *  the browser scrubs, plays and recolours them locally, so the slider is as smooth as the screen allows. */

import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/endpoints'
import type { FireRequest, RiskRegionsResponse } from '../../api/types'
import { EChart } from '../../charts/EChart'
import { timelineOption } from '../../charts/options'
import { Compass } from '../../components/Compass'
import { Slider } from '../../components/Slider'
import Terrain3D from '../../components/Terrain3D'
import { Badge, Banner, Card, ErrorBox, Kpi, KpiRow, Section, Tabs, tierTone } from '../../components/ui'
import { useAsync, useDebounced } from '../../hooks'
import { fixed } from '../../lib/format'
import { decodeFire, MAX_HOURS, timelineIndex, type FireMode } from '../../lib/fire'
import { useApp } from '../../state'

const FORECAST_MODELS = ['XGBoost', 'ARIMA', 'Persistence'] as const

/** Fire simulator: three tiered models on 3D terrain with local, network-free time playback. */
export default function Fire({ info }: { info: RiskRegionsResponse }) {
  const { state } = useApp()
  const [cell, setCell] = useState({ row: 40, col: 40 })
  const [wind, setWind] = useState(20)
  const [deg, setDeg] = useState(45)
  const [source, setSource] = useState<'forecast' | 'manual'>('manual')
  const [fmodel, setFmodel] = useState<(typeof FORECAST_MODELS)[number]>('XGBoost')
  const [manual, setManual] = useState(0.3)
  const [mode, setMode] = useState<FireMode>('deterministic')
  const [hour, setHour] = useState(5)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [note, setNote] = useState<string | null>(null)

  const request: FireRequest = {
    region: state.region, row: cell.row, col: cell.col, wind_kmh: wind, wind_toward_deg: deg, wetness_source: source,
    forecast_model: fmodel, manual_wetness: manual, horizon: state.horizon, n_runs: 24,
  }
  const key = useDebounced(JSON.stringify(request), 220)
  const sim = useAsync(() => api.fire(JSON.parse(key) as FireRequest), [key])
  const data = useMemo(() => (sim.data ? decodeFire(sim.data) : null), [sim.data])

  // playback: advance the clock every animation frame
  useEffect(() => {
    if (!playing) return
    let raf = 0
    let last = performance.now()
    const tick = (now: number) => {
      const dt = (now - last) / 1000
      last = now
      setHour((h) => Math.min(MAX_HOURS, h + dt * speed))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [playing, speed])
  useEffect(() => { if (playing && hour >= MAX_HOURS) setPlaying(false) }, [hour, playing])

  const timeline = sim.data?.timeline
  const idx = timeline ? timelineIndex(hour, timeline.hours.length) : 0
  const chart = useMemo(() => (timeline ? timelineOption(timeline, timeline.hours[idx]!) : null), [timeline, idx])
  const area = timeline ? [timeline.detHa, timeline.probHa, timeline.partHa][['deterministic', 'probabilistic', 'particle'].indexOf(mode)]![idx]! : 0

  const save = async () => {
    if (!sim.data || !timeline) return
    try {
      const r = await api.saveRun({
        region: state.region, forecast_model: sim.data.wetnessSource, forecast_wetness: sim.data.wetness, dryness: sim.data.dryness,
        wind_speed_ms: wind / 3.6, wind_toward_deg: deg, ignition_row: cell.row, ignition_col: cell.col, hours: Math.max(hour, 0.25),
        det_burned_ha: timeline.detHa[idx], prob_burned_ha: timeline.probHa[idx], iou: timeline.iouDetProb[idx],
      })
      setNote(`Saved run #${r.id} to the history.`)
    } catch (e) {
      setNote((e as Error).message)
    }
  }

  return (
    <div className="fade-in">
      <Banner eyebrow="Required · Advanced · Optional" headline="Three models, one scenario" tone="none">
        Fuel dryness comes from the soil-wetness forecast, so a drier forecast means a faster fire. Click the ground to move the ignition
        point, drag to orbit, and press play.
      </Banner>

      <div className="fire-layout">
        <div className="stack">
          <div className="stage-box stage-tall">
            {data && <Terrain3D data={data} mode={mode} tMin={hour * 60} ignition={cell} windDeg={deg} onPick={(row, col) => setCell({ row, col })} />}
            {(sim.loading || !data) && <div className="loading-veil"><div className="spinner" /></div>}
            <div className="overlay tl"><span className="chip-pill">{info.fireModels.find((m) => m.id === mode)!.name} · hour {hour.toFixed(1)} of {MAX_HOURS}</span></div>
            <div className="overlay br"><span className="chip-pill">orange = burning · dark = burned out</span></div>
            {sim.data && <div className="overlay bl"><span className="chip-pill">{sim.data.terrainSource} · heights ×{data!.exaggeration.toFixed(0)} (display only)</span></div>}
          </div>
          <Card className="tight">
            <div className="playbar">
              <button className="btn primary" aria-label={playing ? 'Pause' : 'Play'}
                onClick={() => { if (!playing && hour >= MAX_HOURS) setHour(0); setPlaying(!playing) }}>{playing ? '❚❚' : '▶'}</button>
              <div style={{ flex: 1 }}><Slider label="Time since ignition" value={hour} min={0} max={MAX_HOURS} step={0.05}
                onChange={(v) => { setPlaying(false); setHour(v) }} format={(v) => `${v.toFixed(1)} h`} /></div>
              <label className="field" style={{ width: 110 }}>Speed
                <select value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                  <option value={0.5}>0.5 h/s</option><option value={1}>1 h/s</option><option value={2}>2 h/s</option><option value={4}>4 h/s</option>
                </select>
              </label>
            </div>
          </Card>
        </div>

        <div className="stack">
          <Card>
            <div className="stack">
              <b>Fuel dryness</b>
              <Tabs label="Dryness source" value={source} onChange={setSource}
                options={[{ id: 'forecast', label: 'From forecast' }, { id: 'manual', label: 'What-if' }]} />
              {source === 'forecast' ? (
                <label className="field">Forecast model
                  <select value={fmodel} onChange={(e) => setFmodel(e.target.value as typeof fmodel)}>
                    {FORECAST_MODELS.map((m) => <option key={m}>{m}</option>)}
                  </select>
                </label>
              ) : (
                <Slider label="Soil wetness (0 dry, 1 wet)" value={manual} min={0.15} max={0.85} step={0.01} onChange={setManual} format={(v) => v.toFixed(2)} />
              )}
              {sim.data && <p className="note">Soil wetness <b>{fixed(sim.data.wetness, 3)}</b> ({sim.data.wetnessSource}) gives fuel dryness <b>{fixed(sim.data.dryness, 2)}</b>.</p>}
            </div>
          </Card>
          <Card>
            <div className="stack">
              <b>Wind</b>
              <div className="row" style={{ flexWrap: 'nowrap' }}>
                <Compass value={deg} onChange={setDeg} />
                <div style={{ flex: 1 }}>
                  <p className="note" style={{ marginBottom: 8 }}>Blows toward <b>{deg}°</b></p>
                  <Slider label="Speed" value={wind} min={0} max={60} onChange={setWind} format={(v) => `${v} km/h`} />
                </div>
              </div>
            </div>
          </Card>
          <Card>
            <div className="stack">
              <b>Ignition point</b>
              <p className="note">Row {cell.row}, column {cell.col} of 80 ({(cell.col * 30 / 1000).toFixed(2)} km east, {(cell.row * 30 / 1000).toFixed(2)} km north). Click the terrain to move it.</p>
              <button className="btn block" onClick={save} disabled={!sim.data}>Save this run</button>
              {note && <p className="note" role="status">{note}</p>}
            </div>
          </Card>
        </div>
      </div>
      {sim.error && <ErrorBox error={sim.error} />}

      <Section title="Choose a model" sub="One robust model is required, a second is for comparison, and a third is optional (the instructor's guidance)." />
      <div className="grid cols-3">
        {info.fireModels.map((m) => (
          <button key={m.id} className={`model-card ${mode === m.id ? 'on' : ''}`} onClick={() => setMode(m.id)}>
            <Badge label={m.tier} tone={tierTone(m.tier)} />
            <h4>{m.name}</h4>
            <p>{m.summary}</p>
          </button>
        ))}
      </div>

      {timeline && (
        <>
          <KpiRow>
            <Kpi label="Burned area, this model" value={`${fixed(area, 1)} ha`} sub={`at hour ${hour.toFixed(1)}`} />
            <Kpi label="Fire front length" value={`${fixed(timeline.frontKm[idx], 1)} km`} sub={`${timeline.patches[idx]} burned patch${timeline.patches[idx] === 1 ? '' : 'es'} (deterministic)`} />
            <Kpi label="Agreement: grid vs Monte Carlo" value={fixed(timeline.iouDetProb[idx], 2)} sub="IoU: 1 = identical burned area" />
            <Kpi label="Agreement: grid vs particle" value={fixed(timeline.iouDetPart[idx], 2)} sub="IoU: 1 = identical burned area" />
          </KpiRow>
          <Section title="How fast does each model burn?" sub="Burned area over time. The dashed line marks the current time." />
          <Card className="tight">{chart && <EChart option={chart} height={320} label="Burned area over time for three models" />}</Card>
          <p className="note" style={{ marginTop: 8 }}>
            Validation so far: on flat calm ground the exact answer is a circle of radius rate × time. The grid model under-reaches it by about
            10% (8-neighbour bias) and the particle model overshoots by about 9%, so they bracket the truth. We have not yet compared with
            real burn perimeters.
          </p>
        </>
      )}
    </div>
  )
}
