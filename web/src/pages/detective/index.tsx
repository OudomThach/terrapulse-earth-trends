/** Trend Detective: pick a place, ask a question or scan 20 variables, test each trend for significance. */

import { lazy, Suspense, useEffect } from 'react'
import { prefetch } from '../../api/client'
import { api, trendsUrl } from '../../api/endpoints'
import { ErrorBox, Skeleton, Tabs } from '../../components/ui'
import { useAsync } from '../../hooks'
import { useMeta } from '../../meta'
import { CUSTOM, STAGES, useApp, type AppState } from '../../state'
import { CaseBuilder } from './CaseBuilder'
import { How } from './How'
import { Suspects } from './Suspects'

const Evidence = lazy(() => import('./Evidence').then((m) => ({ default: m.Evidence })))
const Links = lazy(() => import('./Links').then((m) => ({ default: m.Links })))
const World = lazy(() => import('./World').then((m) => ({ default: m.World })))

const DEMOS: { title: string; text: string; patch: Partial<AppState> }[] = [
  { title: 'The Arctic fast lane', text: 'Does the far north warm faster than the rest of the planet? Look at the nights.',
    patch: { place: 'Svalbard, Arctic', code: 'T2M_MIN', stage: 'evidence' } },
  { title: 'Cooling in a warming world', text: 'One of few places where the air is not warming. Follow the sunlight and the haze.',
    patch: { place: 'Delhi & Gangetic plain', code: 'ALLSKY_SFC_SW_DWN', stage: 'evidence' } },
  { title: 'The roof of the world turns wetter', text: 'Warmer and wetter at once. How many vital signs shift together?',
    patch: { place: 'Tibetan Plateau', code: 'PRECTOTCORR', stage: 'evidence' } },
  { title: 'Trend or data glitch?', text: "A 'significant' trend that hides a sudden jump. Can the detective catch it?",
    patch: { place: 'Greenland ice sheet', code: 'CLOUD_AMT', stage: 'evidence' } },
  { title: 'Heat on the Mediterranean', text: 'A climate-change hotspot: scan everything and see what stands out.',
    patch: { place: 'Mediterranean Spain', code: 'T2M', stage: 'suspects' } },
]

function Hero() {
  return (
    <div className="hero">
      <div className="eyebrow">Earth system · Trend Detective</div>
      <h1>Is the planet changing where you live?</h1>
      <p className="lead">
        Pick any place on Earth. We pull 36 years of satellite-based records, scan 20 vital signs, and test each one for a real,
        statistically significant trend. Ask a question, or follow the clues yourself.
      </p>
      <div className="steps">
        {['Choose a place', 'Ask a question', 'Test the evidence', 'Compare the world'].map((s, i) => (
          <div className="step" key={s}><b>{i + 1}</b>{s}</div>
        ))}
      </div>
    </div>
  )
}

/** Trend Detective: the five-stage investigation flow. */
export default function Detective() {
  const { state, patch, placeRef, years } = useApp()
  const { meta } = useMeta()
  const scan = useAsync(() => api.scan(placeRef, years), [JSON.stringify(placeRef), years.start, years.end])
  const place = scan.data?.place ?? meta.places.find((p) => p.name === state.place)

  // While the browser is idle, download the chart code so opening Evidence feels instant.
  useEffect(() => {
    const g = globalThis as unknown as { requestIdleCallback?: (cb: () => void) => number }
    const idle = g.requestIdleCallback ?? ((cb: () => void) => setTimeout(cb, 600))
    idle(() => { void import('./Evidence'); void import('./Links') })
  }, [])

  // Warm the cache for the screens the user is most likely to open next, so they feel instant.
  useEffect(() => {
    if (!scan.data) return
    prefetch(trendsUrl.correlations(placeRef, years))
    const top = scan.data.results.filter((r) => r.usable).sort((a, b) => (a.usable && b.usable ? (a.q ?? 1) - (b.q ?? 1) : 0))[0]
    if (top) prefetch(trendsUrl.series(placeRef, years, top.code))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scan.data])

  return (
    <>
      <Hero />
      <div className="row" style={{ marginBottom: 16, alignItems: 'stretch', flexWrap: 'nowrap', overflowX: 'auto', paddingBottom: 8 }} aria-label="Demo investigations">
        {DEMOS.map((d) => (
          <button key={d.title} className="model-card" style={{ minWidth: 230, flex: '0 0 230px' }}
            onClick={() => patch({ ...d.patch, start: 1990, end: 2025, question: null })}>
            <span className="eyebrow">Watch a demo</span>
            <h4>{d.title}</h4>
            <p>{d.text}</p>
          </button>
        ))}
      </div>
      <CaseBuilder />
      {place && (
        <div className="row" style={{ margin: '16px 0 8px', gap: 24 }}>
          <b style={{ fontSize: 20 }}>{state.place === CUSTOM ? `Custom (${state.lat}, ${state.lon})` : place.name}</b>
          <span className="muted" style={{ fontSize: 14 }}>
            {place.lat.toFixed(2)}°, {place.lon.toFixed(2)}° · {place.biome} · {years.start}–{years.end} · {(years.end - years.start + 1) * 12} months · 20 variables
          </span>
          <span style={{ flexBasis: '100%', fontSize: 14 }}>{place.blurb}</span>
        </div>
      )}
      <div style={{ margin: '8px 0 24px' }}>
        <Tabs label="Stage" value={state.stage} onChange={(stage) => patch({ stage })}
          options={STAGES.map((s, i) => ({ id: s.id, label: `${i + 1} · ${s.label}` }))} />
      </div>

      {scan.error && <ErrorBox error={scan.error} />}
      {!scan.data && !scan.error && (
        <div className="stack">
          <Skeleton height={140} />
          <p className="note">{state.place === CUSTOM ? 'Downloading 36 years of records for this spot (about 5 seconds)…' : 'Reading the record…'}</p>
        </div>
      )}
      {scan.data && (
        <div key={state.stage} style={{ opacity: scan.loading ? 0.6 : 1, transition: 'opacity .2s' }}>
          {state.stage === 'suspects' && <Suspects scan={scan.data} onOpen={(code) => patch({ code, stage: 'evidence' })} />}
          <Suspense fallback={<Skeleton height={360} />}>
            {state.stage === 'evidence' && <Evidence />}
            {state.stage === 'world' && <World />}
            {state.stage === 'links' && <Links />}
          </Suspense>
          {state.stage === 'how' && <How />}
        </div>
      )}
    </>
  )
}
