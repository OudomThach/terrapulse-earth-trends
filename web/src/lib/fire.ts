/** Client-side fire maths: decode the API payload and colour terrain vertices for any moment in time.
 *  Because the server sends arrival times (not frames), scrubbing the slider needs no network calls. */

import type { FireResponse } from '../api/types'
import { clamp } from './format'

export type FireMode = 'deterministic' | 'probabilistic' | 'particle'
export const EXAGGERATION = 2.4

/** Vertical exaggeration for drawing: flat real terrain is stretched so it is visible, rugged terrain is left alone.
 *  This only affects the picture; the fire physics always uses the true elevations. */
export function exaggerationFor(spanM: number): number {
  return clamp(240 / (spanM || 1), 1, 10)
}
export const TIMELINE_STEP_H = 0.25
export const MAX_HOURS = 12

export interface FireData {
  rows: number
  cols: number
  cellM: number
  dem: Float32Array // metres
  minElev: number
  exaggeration: number // display only
  elev01: Float32Array // 0..1 within the tile
  shade: Float32Array // baked lighting, 0.5..1
  deterministic: Float32Array // minutes (Infinity = never)
  particle: Float32Array
  ensemble: Uint8Array // runs x cells, in `quantumMin` steps; `never` = not reached
  runs: number
  quantumMin: number
  never: number
}

/** Convert a list with nulls to a Float32Array, using a fallback for missing values. */
export function toFloat32(values: (number | null)[], fallback = Number.POSITIVE_INFINITY): Float32Array {
  const out = new Float32Array(values.length)
  for (let i = 0; i < values.length; i++) out[i] = values[i] ?? fallback
  return out
}

/** Decode a base64 string into bytes (used for the compact Monte Carlo grid). */
export function decodeBase64(b64: string): Uint8Array {
  const bin = atob(b64)
  const out = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i)
  return out
}

/** Baked lambert-style shading from the terrain slope, so a flat-colour mesh still reads as 3D. */
export function bakeShade(dem: Float32Array, rows: number, cols: number, cellM: number, exaggeration = EXAGGERATION): Float32Array {
  const shade = new Float32Array(rows * cols)
  const lx = -0.45, ly = 0.8, lz = -0.4 // direction towards the light: west, up, north
  const len = Math.hypot(lx, ly, lz)
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const e = dem[r * cols + Math.min(cols - 1, c + 1)]! - dem[r * cols + Math.max(0, c - 1)]!
      const n = dem[Math.min(rows - 1, r + 1) * cols + c]! - dem[Math.max(0, r - 1) * cols + c]!
      const dx = (e * exaggeration) / (2 * cellM) // height change per metre going east
      const dn = (n * exaggeration) / (2 * cellM) // height change per metre going north
      const nx = -dx, ny = 1, nz = dn // surface normal (z points south, so +north gradient tilts it south)
      const nl = Math.hypot(nx, ny, nz)
      const d = (nx * lx + ny * ly + nz * lz) / (nl * len)
      shade[r * cols + c] = 0.5 + 0.5 * clamp(d, 0, 1)
    }
  }
  return shade
}

/** Turn the fire API reply into typed arrays ready for the 3D view. */
export function decodeFire(r: FireResponse): FireData {
  const { rows, cols, cellM } = r.grid
  const dem = toFloat32(r.dem, 0)
  let lo = Infinity, hi = -Infinity
  for (const v of dem) { lo = Math.min(lo, v); hi = Math.max(hi, v) }
  const span = hi - lo || 1
  const elev01 = dem.map((v) => (v - lo) / span)
  const exaggeration = exaggerationFor(span)
  return {
    rows, cols, cellM, dem, minElev: lo, exaggeration, elev01, shade: bakeShade(dem, rows, cols, cellM, exaggeration),
    deterministic: toFloat32(r.deterministic), particle: toFloat32(r.particle),
    ensemble: decodeBase64(r.ensemble.data), runs: r.ensemble.runs, quantumMin: r.ensemble.quantumMin, never: r.ensemble.never,
  }
}

type RGB = readonly [number, number, number]
const LOW: RGB = [0.31, 0.48, 0.23]
const HIGH: RGB = [0.76, 0.67, 0.45]
const CHAR: RGB = [0.2, 0.2, 0.21]
const YOUNG: RGB = [1.0, 0.86, 0.45]
const OLD: RGB = [0.93, 0.27, 0.1]
const PALE: RGB = [1.0, 0.9, 0.55]
const ORANGE: RGB = [1.0, 0.42, 0.05]
const DARK_RED: RGB = [0.5, 0.02, 0.02]

const mix = (a: RGB, b: RGB, t: number): RGB => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]

/** Heat colour for a burn probability 0..1. */
export function heat(p: number): RGB {
  return p < 0.5 ? mix(PALE, ORANGE, p / 0.5) : mix(ORANGE, DARK_RED, (p - 0.5) / 0.5)
}

/** Fill ``out`` (rgb per vertex) with the colours for time ``tMin`` minutes after ignition. */
export function colorize(out: Float32Array, d: FireData, mode: FireMode, tMin: number, flameMin = 45): void {
  const n = d.rows * d.cols
  const put = (i: number, c: RGB, k = 1) => {
    out[i * 3] = c[0] * k
    out[i * 3 + 1] = c[1] * k
    out[i * 3 + 2] = c[2] * k
  }
  const ground = (i: number) => put(i, mix(LOW, HIGH, d.elev01[i]!), d.shade[i]!)
  if (mode === 'probabilistic') {
    const limit = tMin / d.quantumMin
    for (let i = 0; i < n; i++) {
      let hits = 0
      for (let r = 0; r < d.runs; r++) {
        const q = d.ensemble[r * n + i]!
        if (q !== d.never && q <= limit) hits++
      }
      if (hits === 0) ground(i)
      else put(i, heat(hits / d.runs))
    }
    return
  }
  const arrival = mode === 'deterministic' ? d.deterministic : d.particle
  for (let i = 0; i < n; i++) {
    const a = arrival[i]!
    if (a > tMin) ground(i)
    else {
      const age = tMin - a
      if (age < flameMin) put(i, mix(YOUNG, OLD, age / flameMin))
      else put(i, CHAR, 0.8 + 0.3 * d.shade[i]!)
    }
  }
}

/** Index into the server's quarter-hour timeline for ``hour``. */
export function timelineIndex(hour: number, length: number): number {
  return clamp(Math.round(hour / TIMELINE_STEP_H), 0, length - 1)
}
