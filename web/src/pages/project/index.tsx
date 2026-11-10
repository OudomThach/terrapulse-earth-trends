/** Project: the instructor's feedback and the proposal's requirements, mapped to where each is met. */

import { Badge, Card, Section } from '../../components/ui'
import { useMeta } from '../../meta'
import { useApp } from '../../state'

const MARK: Record<string, string> = { done: '✓', partial: '◐', optional: '○', todo: '✗' }
const LABEL: Record<string, string> = { done: 'Done', partial: 'Partly done', optional: 'Optional', todo: 'Not done' }

const LAYERS: [string, string][] = [
  ['Browser', 'React + TypeScript. Three.js terrain, MapLibre globe, ECharts. Scrubs the fire timeline locally.'],
  ['API', 'FastAPI. Validated requests, gzip, caching, background jobs, timing headers.'],
  ['Logic', 'terrapulse package: Mann-Kendall and Sen statistics, ARIMA and XGBoost, three fire models.'],
  ['Data', 'Satellite reanalysis records cached on disk; SQLite for saved runs and benchmarks.'],
  ['Delivery', 'Multi-stage Docker image and Compose; one command starts everything.'],
]

/** Project page: instructor feedback mapped to answers, and the honest proposal checklist. */
export default function Project() {
  const { meta } = useMeta()
  const { patch } = useApp()
  return (
    <div className="fade-in">
      <div className="hero">
        <div className="eyebrow">Project</div>
        <h1>What the instructor asked for, and where it is met.</h1>
        <p className="lead">Each piece of written feedback on the proposal, the answer, and where to see it working.</p>
      </div>

      <div className="stack">
        {meta.feedback.map((f) => (
          <Card key={f.id}>
            <div className="grid cols-2" style={{ gap: 32 }}>
              <div>
                <span className="eyebrow">Instructor feedback</span>
                <p style={{ marginTop: 8, fontStyle: 'italic' }}>"{f.instructor}"</p>
              </div>
              <div>
                <span className="eyebrow">What we did</span>
                <p style={{ marginTop: 8 }}>{f.response}</p>
                <p className="note" style={{ marginTop: 8 }}><Badge label={LABEL[f.status] ?? f.status} tone="required" /> Where to see it: <b>{f.where}</b>{' '}
                  <button className="btn small" onClick={() => patch({ view: 'risk', riskTab: f.id === 'simulation' ? 'fire' : 'forecast' })}>Open</button></p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Section title="Proposal checklist" sub="Marked honestly: what is done, partly done, optional, or not done." />
      <Card>
        {meta.requirements.map((r) => (
          <div className="check" key={r.item}>
            <span className={`mark ${r.status}`} aria-label={LABEL[r.status]}>{MARK[r.status]}</span>
            <span>{r.item}<br /><span className="muted">{r.where}</span></span>
            <Badge label={LABEL[r.status]!} tone={r.status === 'done' ? 'required' : r.status === 'optional' ? 'optional' : 'weak'} />
          </div>
        ))}
      </Card>

      <Section title="How it is built" sub="Each layer can be run and tested on its own." />
      <div className="how">
        {LAYERS.map(([h, p], i) => <Card key={h}><div className="n">LAYER {i + 1}</div><h4>{h}</h4><p>{p}</p></Card>)}
      </div>
      <p className="note" style={{ marginTop: 16 }}>
        Interactive API documentation is at <a href="/docs">/docs</a>. Version {meta.version}.
      </p>
    </div>
  )
}
