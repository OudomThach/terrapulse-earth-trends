/** Design tokens (mirrors terrapulse/theme.py): dark surface, validated categorical colours,
 *  and a blue-to-red diverging pair whose colour means direction, never good or bad. */

export const C = {
  bg: '#0b0d10',
  surface: '#15181c',
  surface2: '#1d2126',
  line: '#262b31',
  lineStrong: '#363c44',
  ink: '#f0efec',
  ink2: '#c3c2b7',
  muted: '#898781',
  blue: '#3987e5',
  orange: '#d95926',
  aqua: '#199e70',
  violet: '#9085e9',
  rise: '#e66767',
  fall: '#3987e5',
  neutral: '#383835',
  accent: '#3fd4a2',
} as const

export const FONT = "'Inter Variable', system-ui, -apple-system, 'Segoe UI', sans-serif"

/** Colour for a signed value on the diverging scale, clamped at ±zmax. Returns an rgb() string. */
export function diverging(value: number, zmax: number, neutral = '#8a8985'): string {
  const t = Math.max(-1, Math.min(1, zmax > 0 ? value / zmax : 0))
  const hex = (h: string): [number, number, number] => [
    parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16),
  ]
  const from = hex(neutral)
  const to = hex(t >= 0 ? C.rise : C.fall)
  const k = Math.abs(t)
  const mix = from.map((f, i) => Math.round(f + (to[i]! - f) * k))
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`
}
