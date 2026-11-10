/** Stage 4: what the significant trends say together, and which variables move together. */

import { useMemo } from 'react'
import { api } from '../../api/endpoints'
import { EChart } from '../../charts/EChart'
import { correlationOption } from '../../charts/options'
import { Card, ErrorBox, Section, Skeleton } from '../../components/ui'
import { useAsync } from '../../hooks'
import { signed } from '../../lib/format'
import { useApp } from '../../state'

/** Connections stage: how variables move together, with physical explanations. */
export function Links() {
  const { placeRef, years } = useApp()
  const { data, error, loading } = useAsync(() => api.correlations(placeRef, years), [JSON.stringify(placeRef), years.start, years.end])
  const heat = useMemo(() => (data ? correlationOption(data) : null), [data])

  return (
    <div className="fade-in">
      <Section title="What the significant trends say together"
        sub="Individual trends become a story when they agree with the physics. These readings are 'consistent with', not proof of cause." />
      {error && <ErrorBox error={error} />}
      {!data && !error && <Skeleton height={200} />}
      {data && (
        <div style={{ opacity: loading ? 0.6 : 1, transition: 'opacity .2s' }}>
          {data.story.length > 0 ? (
            <div className="story">
              {data.story.map((s) => <Card key={s.title}><h4>{s.title}</h4><p>{s.text}</p></Card>)}
            </div>
          ) : (
            <p className="note">No clear multi-variable story here: few variables passed the significance test. Try a longer window or a different place.</p>
          )}

          <Section title="How the variables move together"
            sub="Month-to-month wiggles with the seasons and long-term trends removed, so these links are not just two trends that happen to coincide." />
          <div className="grid side">
            <Card className="tight">
              {heat && <EChart option={heat} height={640} label="Heatmap of link strength between variables" />}
              <p className="note">Red: when one is above normal, the other tends to be too. Blue: when one is high, the other tends to be low. Grey: little link.</p>
            </Card>
            <div className="stack">
              <b>Strongest explainable links</b>
              {data.links.length === 0 && <p className="note">No strong links found.</p>}
              {data.links.map((l) => (
                <Card key={`${l.a}-${l.b}`} className="tight">
                  <b>{l.aName}</b> and <b>{l.bName}</b> {l.rho > 0 ? 'move together' : 'move in opposite directions'} ({signed(l.rho, 2)}).
                  {l.note && <p style={{ marginTop: 8, fontSize: 14 }}>{l.matches === null ? '' : l.matches ? '✓ ' : '⚠ '}{l.note}</p>}
                </Card>
              ))}
            </div>
          </div>
          <p className="note" style={{ marginTop: 16 }}>
            Correlation shows that two things move together, not that one causes the other. Explanations marked ✓ are well-understood physical
            links; ⚠ marks a relationship that is the opposite of the usual expectation here.
          </p>
        </div>
      )}
    </div>
  )
}
