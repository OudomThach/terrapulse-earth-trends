/** Number and text formatting shared by every screen. Mirrors terrapulse/narrative.py. */

export const MINUS = '−'

/** +1.23 / −0.40 with a real minus sign. */
export function signed(v: number | null | undefined, decimals = 2): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return 'n/a'
  const s = v.toLocaleString('en-US', { signDisplay: 'always', minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  return s.replace('-', MINUS)
}

/** Format a number to fixed decimals, or a dash when missing. */
export function fixed(v: number | null | undefined, decimals = 2): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return 'n/a'
  return v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

/** Chance of a pattern this strong arising by luck, in words. */
export function plainP(p: number): string {
  if (p < 0.001) return 'less than 1 time in 1,000'
  if (p < 0.01) return `about ${Math.max(1, Math.round(p * 1000))} times in 1,000`
  if (p < 0.995) return `about ${Math.round(p * 100)} times in 100`
  return 'almost every time'
}

/** Format a p-value, showing 'less than 0.001' for very small values. */
export function pText(p: number | null | undefined): string {
  if (p === null || p === undefined) return 'n/a'
  return p < 0.001 ? 'p < 0.001' : `p = ${p.toFixed(3)}`
}

/** Evidence meter that does not rely on colour. */
export function strengthDots(p: number): string {
  return p < 0.01 ? '●●●' : p < 0.05 ? '●●○' : p < 0.1 ? '●○○' : '○○○'
}

/** Arrow symbol for a trend direction. */
export function arrow(direction: string): string {
  return direction === 'rising' ? '▲' : direction === 'falling' ? '▼' : '–'
}

/** CSS class name (rise, fall or flat) for a trend direction. */
export function directionClass(direction: string): 'rise' | 'fall' | 'flat' {
  return direction === 'rising' ? 'rise' : direction === 'falling' ? 'fall' : 'flat'
}

export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Clamp ``v`` into [lo, hi]. */
export const clamp = (v: number, lo: number, hi: number): number => Math.min(hi, Math.max(lo, v))
