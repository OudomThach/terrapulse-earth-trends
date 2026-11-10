/** Stage 3: the same variable at every place, so opposite trends show up side by side. */

import { lazy, Suspense, useMemo, useState } from 'react'
import { api } from '../../api/endpoints'
import { EChart } from '../../charts/EChart'
import { rankedBarsOption } from '../../charts/options'
import { VariableSelect } from '../../components/VariableSelect'
import { Banner, Card, DataTable, ErrorBox, Kpi, KpiRow, RichText, Section, Skeleton, Toggle } from '../../components/ui'
import { useAsync } from '../../hooks'
import { fixed } from '../../lib/format'
import { useMeta } from '../../meta'
import { useApp } from '../../state'

const WorldMap = lazy(() => import('../../components/WorldMap'))

/** Globe stage: compare one variable across places. */
export function World() {
  const { state, patch, placeRef, years } = useApp()
  const { variable, meta } = useMeta()
  const [satellite, setSatellite] = useState(true)
  const [live, setLive] = useState(false)
  const [table, setTable] = useState(false)
  const code = state.mapCode
  const v = variable(code)!


  const regional = useAsync(() => api.regional(placeRef, years, code), [JSON.stringify(placeRef), years.start, years.end, code])
  const events = useAsync(() => (live ? api.events().then((e) => e.events) : Promise.resolve(null)), [live])
  const data = regional.data
  const bars = useMemo(() => (data && data.rows.length ? rankedBarsOption(data.rows, v.unit, v.decimals) : null), [data, v.unit, v.decimals])
  const placeNames = new Set(meta.places.map((p) => p.name))

  return (
    <div className="fade-in">
      <Section title="Same question, everywhere"
        sub="The same variable can rise in one place and fall in another, even when one process drives both. Pick a variable and compare all places." />
      <div className="row" style={{ alignItems: 'flex-end' }}>
        <div style={{ minWidth: 280, flex: '1 1 280px' }}>
          <VariableSelect label="Variable" value={code} onChange={(c) => patch({ mapCode: c, mapFollows: false })} />
        </div>
        <Toggle label="Satellite imagery" checked={satellite} onChange={setSatellite} />
        <Toggle label="Live natural events" checked={live} onChange={setLive} />
      </div>

      {regional.error && <ErrorBox error={regional.error} />}
      {!data && !regional.error && <Skeleton height={520} className="" />}
      {data && data.rows.length === 0 && <Banner headline="No testable record in this window" tone="none" />}
      {data && data.rows.length > 0 && (
        <div style={{ opacity: regional.loading ? 0.6 : 1, transition: 'opacity .2s' }}>
          <KpiRow>
            <Kpi label="Significantly rising" value={data.finding.rising ?? 0} sub={`of ${data.rows.length} places`} tone="rise" />
            <Kpi label="Significantly falling" value={data.finding.falling ?? 0} sub={`of ${data.rows.length} places`} tone="fall" />
            <Kpi label="No clear trend" value={data.finding.none ?? 0} sub="natural variation can't be ruled out" />
          </KpiRow>
          {data.finding.kind !== 'none' && (
            <Banner eyebrow="Detective's finding" headline={data.finding.headline} tone="sig"><RichText text={data.finding.body} /></Banner>
          )}
          {live && events.data === undefined && events.error && <p className="note">The live event feed is not reachable right now. The trend map is unaffected.</p>}
          <div className="legend">
            <span><i style={{ background: 'var(--rise)' }} />Rising</span>
            <span><i style={{ background: 'var(--fall)' }} />Falling</span>
            <span>Large ringed dots are significant after correcting for comparing many places; small faded dots are not</span>
          </div>
          <div className="stage-box" style={{ height: 540 }}>
            <Suspense fallback={<div className="loading-veil"><div className="spinner" /></div>}>
              <WorldMap rows={data.rows} unit={v.unit} decimals={v.decimals} satellite={satellite} selected={state.place}
                events={events.data ?? null} onSelect={(name) => placeNames.has(name) && patch({ place: name, stage: 'suspects', question: null })} />
            </Suspense>
            <div className="overlay tl"><span className="chip-pill">Click a dot to investigate that place · drag to rotate · scroll to zoom</span></div>
          </div>

          <Section title="Ranked" sub="Same data as the map, sorted from most-falling to most-rising." />
          <Card className="tight">{bars && <EChart option={bars} height={Math.max(360, data.rows.length * 26 + 60)} label="Trend by place" />}</Card>
          <div style={{ marginTop: 16 }}><Toggle label="Show the data table" checked={table} onChange={setTable} /></div>
          {table && (
            <div style={{ marginTop: 16 }}>
              <DataTable columns={['Place', 'Biome', `${v.unit} / decade`, 'p', 'adj. p', 'Significant', 'Data jump']}
                rows={data.rows.map((r) => [r.name, r.biome, fixed(r.perDecade, v.decimals + 1), r.p.toFixed(4), r.q.toFixed(4), r.significant ? 'yes' : 'no', r.jump ? 'possible' : ''])} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
