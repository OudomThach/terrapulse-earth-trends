/** Small presentational building blocks. No data fetching in here. */

import type { CSSProperties, ReactNode } from 'react'
import type { Tone } from '../api/types'

/** Titled block of page content with an optional subtitle and action. */
export function Section({ title, sub, action }: { title: string; sub?: string; action?: ReactNode }) {
  return (
    <div className="section">
      <div>
        <h2>{title}</h2>
        {sub && <p>{sub}</p>}
      </div>
      {action}
    </div>
  )
}

/** Padded surface used for grouped content. */
export function Card({ children, className = '', style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  return (
    <div className={`card ${className}`} style={style}>
      {children}
    </div>
  )
}

/** One headline number with a label and a short caption. */
export function Kpi({ label, value, sub, tone, subTone }: {
  label: string
  value: ReactNode
  sub?: ReactNode
  tone?: 'rise' | 'fall'
  subTone?: 'rise' | 'fall'
}) {
  const long = typeof value === 'string' && value.length > 14
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${tone ?? ''} ${long ? 'sm' : ''}`}>{value}</div>
      {sub && <div className={`kpi-sub ${subTone ?? ''}`}>{sub}</div>}
    </div>
  )
}

/** Responsive row of Kpi tiles. */
export function KpiRow({ children }: { children: ReactNode }) {
  return <div className="kpis">{children}</div>
}

/** Highlighted plain-language answer at the top of a page. */
export function Banner({ eyebrow, headline, children, tone = 'none' }: {
  eyebrow?: string
  headline: string
  children?: ReactNode
  tone?: Tone
}) {
  return (
    <div className={`banner ${tone}`} role="status">
      {eyebrow && <div className="eyebrow">{eyebrow}</div>}
      <h3>{headline}</h3>
      {children && <p>{children}</p>}
    </div>
  )
}

/** Render text containing **bold** markers (the API's narrative strings) without using innerHTML. */
export function RichText({ text }: { text: string }) {
  return (
    <>
      {text.split('**').map((part, i) => (i % 2 ? <b key={i}>{part}</b> : <span key={i}>{part}</span>))}
    </>
  )
}

/** Small coloured label. */
export function Badge({ label, tone }: { label: string; tone: 'strong' | 'sig' | 'weak' | 'none' | 'required' | 'advanced' | 'optional' | 'reference' }) {
  return <span className={`badge ${tone}`}>{label}</span>
}

/** Map an evidence label (for example 'Strong') to a badge tone. */
export function evidenceTone(label: string): 'strong' | 'sig' | 'weak' | 'none' {
  return label === 'Strong evidence' ? 'strong' : label === 'Significant' ? 'sig' : label === 'Weak hint' ? 'weak' : 'none'
}

/** Map a model tier (required, advanced, optional) to a badge tone. */
export function tierTone(tier: string): 'required' | 'advanced' | 'optional' | 'reference' {
  const t = tier.toLowerCase()
  return t.startsWith('required') ? 'required' : t.startsWith('advanced') ? 'advanced' : t.startsWith('optional') ? 'optional' : 'reference'
}

/** Single-choice pill selector. */
export function Pills<T extends string>({ options, value, onChange, label }: {
  options: { id: T; label: string }[]
  value: T | null
  onChange: (id: T) => void
  label: string
}) {
  return (
    <div className="pills" role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} role="radio" aria-checked={value === o.id} className={`pill ${value === o.id ? 'on' : ''}`}
          onClick={() => onChange(o.id)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Tab bar for switching between sub-pages. */
export function Tabs<T extends string>({ options, value, onChange, label }: {
  options: { id: T; label: string }[]
  value: T
  onChange: (id: T) => void
  label: string
}) {
  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} role="tab" aria-selected={value === o.id} className={`tab ${value === o.id ? 'on' : ''}`}
          onClick={() => onChange(o.id)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Labelled on/off switch. */
export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="track" aria-hidden />
      <span>{label}</span>
    </label>
  )
}

/** Placeholder block shown while content loads. */
export function Skeleton({ height = 120, className = '' }: { height?: number; className?: string }) {
  return <div className={`skeleton ${className}`} style={{ height }} aria-busy="true" />
}

/** Readable error message with a retry button. */
export function ErrorBox({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <div className="banner warn" role="alert">
      <div className="eyebrow">Something went wrong</div>
      <h3>We could not load this</h3>
      <p>{error.message}</p>
      {retry && <button className="btn" onClick={retry}>Try again</button>}
    </div>
  )
}

/** Inline SVG of the yearly averages (decorative; the numbers beside it carry the meaning). */
export function Sparkline({ values, direction, w = 200, h = 40 }: {
  values: (number | null)[]
  direction: string
  w?: number
  h?: number
}) {
  const v = values.filter((x): x is number => x !== null && Number.isFinite(x))
  if (v.length < 2) return null
  const lo = Math.min(...v)
  const span = Math.max(...v) - lo || 1
  const pts = v.map((y, i) => `${(3 + (i / (v.length - 1)) * (w - 6)).toFixed(1)},${(h - 4 - ((y - lo) / span) * (h - 8)).toFixed(1)}`)
  const last = pts[pts.length - 1]!.split(',')
  const color = direction === 'rising' ? 'var(--rise)' : direction === 'falling' ? 'var(--fall)' : 'var(--muted)'
  return (
    <svg className="spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`} role="img" aria-label="yearly averages over time">
      <polyline points={pts.join(' ')} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r="3.5" fill={color} stroke="var(--surface)" strokeWidth="2" />
    </svg>
  )
}

/** Simple table from column names and rows. */
export function DataTable({ columns, rows }: { columns: string[]; rows: (string | number | null)[][] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{r.map((cell, j) => <td key={j}>{cell ?? '–'}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
