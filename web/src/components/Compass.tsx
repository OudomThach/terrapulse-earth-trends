import { useRef } from 'react'

/** Drag the needle to choose which way the wind blows (compass bearing, 0 = north, 90 = east). */
export function Compass({ value, onChange }: { value: number; onChange: (deg: number) => void }) {
  const ref = useRef<SVGSVGElement>(null)
  const drag = useRef(false)
  const set = (e: React.PointerEvent) => {
    const r = ref.current!.getBoundingClientRect()
    const dx = e.clientX - (r.left + r.width / 2)
    const dy = e.clientY - (r.top + r.height / 2)
    onChange(Math.round(((Math.atan2(dx, -dy) * 180) / Math.PI + 360) % 360))
  }
  const rad = (value * Math.PI) / 180
  const x = 48 + Math.sin(rad) * 34
  const y = 48 - Math.cos(rad) * 34
  return (
    <svg ref={ref} className="compass" viewBox="0 0 96 96" role="slider" aria-label="Wind direction" aria-valuemin={0} aria-valuemax={359}
      aria-valuenow={value} tabIndex={0}
      onPointerDown={(e) => { drag.current = true; e.currentTarget.setPointerCapture(e.pointerId); set(e) }}
      onPointerMove={(e) => drag.current && set(e)} onPointerUp={() => { drag.current = false }}
      onKeyDown={(e) => {
        if (e.key === 'ArrowRight' || e.key === 'ArrowUp') onChange((value + 5) % 360)
        if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') onChange((value + 355) % 360)
      }}>
      <circle cx="48" cy="48" r="44" fill="#15181c" stroke="#363c44" strokeWidth="2" />
      {['N', 'E', 'S', 'W'].map((l, i) => (
        <text key={l} x={48 + Math.sin((i * Math.PI) / 2) * 35} y={51 - Math.cos((i * Math.PI) / 2) * 35} textAnchor="middle" fontSize="9"
          fill={l === 'N' ? '#3fd4a2' : '#898781'}>{l}</text>
      ))}
      <line x1="48" y1="48" x2={x} y2={y} stroke="#7fd1ff" strokeWidth="3" strokeLinecap="round" />
      <circle cx={x} cy={y} r="5" fill="#7fd1ff" />
      <circle cx="48" cy="48" r="3" fill="#f0efec" />
    </svg>
  )
}
