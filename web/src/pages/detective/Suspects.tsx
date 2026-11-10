/** Stage 1: ask a question or scan all 20 variables, ranked by strength of evidence. */

import { useMemo, useState } from 'react'
import { api, trendsUrl } from '../../api/endpoints'
import type { ScanResponse, Trend, TrendOk } from '../../api/types'
import { Banner, Kpi, KpiRow, Pills, RichText, Section, Toggle } from '../../components/ui'
import { useAsync } from '../../hooks'
import { useMeta } from '../../meta'
import { useApp } from '../../state'
import { SuspectCard } from './SuspectCard'

const ALL = 'all'

function Legend() {
  return (
    <div className="legend">
      <span><i style={{ background: 'var(--rise)' }} />Rising</span>
      <span><i style={{ background: 'var(--fall)' }} />Falling</span>
      <span>Colour shows direction, not good or bad</span>
    </div>
  )
}

/** Question pills and the detective's answer. Returns the clue codes the answer is based on (null = all clues). */
function useQuestion() {
  const { state, patch, placeRef, years } = useApp()
  const { meta } = useMeta()
  const options = [{ id: ALL, label: 'All 20 clues' }, ...meta.questions.map((q) => ({ id: q.id, label: q.text })), { id: 'surprise', label: 'Surprise me' }]
  const selected = state.question ?? ALL
  const answer = useAsync(
    () => (state.question ? api.answer(placeRef, years, state.question) : Promise.resolve(undefined)),
    [JSON.stringify(placeRef), years.start, years.end, state.question],
  )
  return { options, selected, answer, choose: (id: string) => patch({ question: id === ALL ? null : id }) }
}

/** Suspects stage: the scan of all variables for one place, with guided questions. */
export function Suspects({ scan, onOpen }: { scan: ScanResponse; onOpen: (code: string) => void }) {
  const { meta } = useMeta()
  const { state, placeRef, years } = useApp()
  const { options, selected, answer, choose } = useQuestion()
  const [group, setGroup] = useState<string>('All')
  const [onlySig, setOnlySig] = useState(false)

  const byCode = useMemo(() => new Map(scan.results.map((r) => [r.code, r])), [scan])
  const ranked = useMemo(
    () => scan.results.filter((r): r is TrendOk => r.usable).sort((a, b) => (a.q ?? 1) - (b.q ?? 1) || Math.abs(b.z) - Math.abs(a.z)),
    [scan],
  )
  const untestable = scan.results.filter((r) => !r.usable)
  const s = scan.summary

  let shown: Trend[]
  if (state.question && answer.data) shown = answer.data.codes.map((c) => byCode.get(c)).filter((r): r is Trend => !!r && r.usable)
  else if (state.question) shown = []
  else shown = ranked.filter((r) => (group === 'All' || r.group === group) && (!onlySig || (r.q ?? 1) < 0.05))

  return (
    <div className="fade-in">
      <Section title="What are you curious about?" sub="Pick a question and the detective answers it from the evidence, or scan everything." />
      <Pills label="Ask the detective" options={options} value={selected} onChange={choose} />

      {state.question && answer.data && (
        <div style={{ marginTop: 16 }}>
          <Banner eyebrow={state.question === 'surprise' ? "Detective's pick" : "Detective's answer"} headline={answer.data.headline} tone={answer.data.tone}>
            <RichText text={answer.data.body} />
          </Banner>
          <p className="note">{answer.data.why}</p>
        </div>
      )}

      {!state.question && (
        <KpiRow>
          <Kpi label="Variables tested" value={s.tested} sub={`of ${s.available} available here`} />
          <Kpi label="Significant trends" value={s.significant} sub="after correcting for testing many variables at once" />
          {s.strongest
            ? <Kpi label="Strongest clear signal" value={s.strongest.name} sub={s.strongest.rateText} subTone={s.strongest.direction === 'rising' ? 'rise' : 'fall'} />
            : <Kpi label="Strongest clear signal" value="None" sub="no variable passed the test" />}
          <Kpi label="Possible data jumps" value={s.jumps} sub="abrupt steps that may be data artefacts" />
        </KpiRow>
      )}

      <Section
        title={state.question ? 'The clues behind the answer' : 'The suspect board'}
        sub={state.question ? 'Strongest evidence first.' : 'Every variable ranked by strength of evidence. Open any card to see the full investigation.'}
        action={!state.question && (
          <a className="btn small" href={trendsUrl.report(placeRef, years)} download>Download case file</a>
        )}
      />
      {!state.question && (
        <div className="row spread" style={{ marginBottom: 8 }}>
          <Pills label="Filter by type" value={group} onChange={setGroup}
            options={['All', ...meta.groups].map((g) => ({ id: g, label: g }))} />
          <Toggle label="Only significant" checked={onlySig} onChange={setOnlySig} />
        </div>
      )}
      <Legend />
      {shown.length === 0 && !answer.loading && <p className="note">No variables match these filters.</p>}
      <div className="suspects">
        {shown.map((t, i) => <SuspectCard key={`${state.question}-${t.code}`} trend={t} index={i} onOpen={onOpen} />)}
      </div>
      {!state.question && untestable.length > 0 && (
        <details style={{ marginTop: 24 }}>
          <summary>{untestable.length} variable(s) could not be tested here</summary>
          <div>{untestable.map((r) => <p key={r.code}><b>{r.name}</b>: {r.usable ? '' : r.reason}</p>)}</div>
        </details>
      )}
    </div>
  )
}
