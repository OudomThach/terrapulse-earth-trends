/** Pick the place and the years. Year sliders are debounced so dragging does not hammer the API. */

import { useEffect, useState } from 'react'
import { Card } from '../../components/ui'
import { Slider } from '../../components/Slider'
import { useDebounced } from '../../hooks'
import { useMeta } from '../../meta'
import { CUSTOM, FIRST_YEAR, LAST_YEAR, useApp } from '../../state'

/** Case stage: build a written case with the numbers, the caveats and a shareable summary. */
export function CaseBuilder() {
  const { state, patch } = useApp()
  const { meta } = useMeta()
  const [range, setRange] = useState<[number, number]>([state.start, state.end])
  const settled = useDebounced(range, 250)
  const [coords, setCoords] = useState({ lat: String(state.lat), lon: String(state.lon) })

  useEffect(() => {
    if (settled[0] !== state.start || settled[1] !== state.end) patch({ start: settled[0], end: settled[1] })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settled])
  useEffect(() => setRange([state.start, state.end]), [state.start, state.end])

  const applyCoords = () => {
    const lat = Number(coords.lat)
    const lon = Number(coords.lon)
    if (Number.isFinite(lat) && Number.isFinite(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180) patch({ place: CUSTOM, lat, lon, stage: 'suspects', question: null })
  }

  return (
    <Card>
      <div className="grid cols-2" style={{ alignItems: 'start', gap: 32 }}>
        <div className="stack">
          <label className="field">
            Where do you want to investigate?
            <select value={state.place} onChange={(e) => patch({ place: e.target.value, question: null })}>
              {meta.places.map((p) => <option key={p.name} value={p.name}>{p.name} · {p.biome}</option>)}
              <option value={CUSTOM}>Custom location…</option>
            </select>
          </label>
          {state.place === CUSTOM && (
            <div className="row" style={{ alignItems: 'flex-end' }}>
              <label className="field" style={{ flex: 1 }}>Latitude<input type="number" step="0.5" min={-90} max={90} value={coords.lat}
                onChange={(e) => setCoords({ ...coords, lat: e.target.value })} onKeyDown={(e) => e.key === 'Enter' && applyCoords()} /></label>
              <label className="field" style={{ flex: 1 }}>Longitude<input type="number" step="0.5" min={-180} max={180} value={coords.lon}
                onChange={(e) => setCoords({ ...coords, lon: e.target.value })} onKeyDown={(e) => e.key === 'Enter' && applyCoords()} /></label>
              <button className="btn primary" onClick={applyCoords}>Go</button>
            </div>
          )}
        </div>
        <div className="stack">
          <div className="grid cols-2">
            <Slider label="From" value={range[0]} min={FIRST_YEAR} max={range[1] - 9} onChange={(v) => setRange([v, range[1]])} />
            <Slider label="To" value={range[1]} min={range[0] + 9} max={LAST_YEAR} onChange={(v) => setRange([range[0], v])} />
          </div>
          <div className="row spread">
            <span className="note">Trends need a long record: at least 10 years.</span>
            {(state.start !== FIRST_YEAR || state.end !== LAST_YEAR) &&
              <button className="btn small" onClick={() => patch({ start: FIRST_YEAR, end: LAST_YEAR })}>Use the full record</button>}
          </div>
        </div>
      </div>
    </Card>
  )
}
