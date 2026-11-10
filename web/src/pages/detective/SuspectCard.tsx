import type { CSSProperties } from 'react'
import type { Trend } from '../../api/types'
import { Badge, evidenceTone, Sparkline } from '../../components/ui'
import { arrow, directionClass, signed } from '../../lib/format'

/** Summary card for one variable: rate, sparkline, evidence badge and any data-jump flag. */
export function SuspectCard({ trend, index, onOpen }: { trend: Trend; index: number; onOpen: (code: string) => void }) {
  const style = { '--i': index } as CSSProperties
  if (!trend.usable) {
    return (
      <div className="suspect" style={style}>
        <div className="suspect-top"><span className="chip">{trend.group}</span></div>
        <div className="suspect-name">{trend.name}</div>
        <p className="note">{trend.reason}</p>
      </div>
    )
  }
  const cls = directionClass(trend.direction)
  const q = trend.q
  return (
    <div className="suspect" style={style}>
      <div className="suspect-top">
        <span className="chip">{trend.group}</span>
        <span className={`meter ${trend.label === 'No clear trend' ? 'dim' : ''}`} title="Strength of evidence">{trend.dots}</span>
      </div>
      <div className="suspect-name">{trend.name}</div>
      <div className={`rate ${cls}`}>
        {arrow(trend.direction)} {signed(trend.perDecade, trend.decimals)}
        <span className="unit">{trend.unit} / decade</span>
      </div>
      <Sparkline values={trend.annual.values} direction={trend.direction} />
      <div className="suspect-foot">
        <Badge label={trend.label} tone={evidenceTone(trend.label)} />
        <span title="p-value after correcting for testing many variables">
          adj. p {q === null ? 'n/a' : q < 0.0005 ? '< 0.001' : `= ${q.toFixed(3)}`}
        </span>
      </div>
      {trend.jump.suspicious && <div className="flag">⚠ Possible data jump in {trend.jump.year}</div>}
      <button className="btn block" onClick={() => onOpen(trend.code)}>Investigate</button>
    </div>
  )
}
