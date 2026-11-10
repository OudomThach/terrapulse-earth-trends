import type { CSSProperties } from 'react'

/** A labelled range input whose track fills up to the thumb. */
export function Slider({ label, value, min, max, step = 1, onChange, format, disabled }: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (v: number) => void
  format?: (v: number) => string
  disabled?: boolean
}) {
  const pct = max > min ? ((value - min) / (max - min)) * 100 : 0
  return (
    <label className="field" style={{ opacity: disabled ? 0.5 : 1 }}>
      <span className="slider-head"><span>{label}</span><b>{format ? format(value) : value}</b></span>
      <input type="range" min={min} max={max} step={step} value={value} disabled={disabled}
        style={{ '--fill': `${pct}%` } as CSSProperties} onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  )
}
