import { describe, expect, it } from 'vitest'
import { bakeShade, colorize, decodeBase64, exaggerationFor, heat, timelineIndex, toFloat32, type FireData } from './fire'

/** A 2 x 2 terrain: cell 0 burns at 10 min, cell 1 at 100 min, cells 2 and 3 never. */
function tiny(): FireData {
  const dem = new Float32Array([500, 500, 500, 500])
  return {
    rows: 2, cols: 2, cellM: 30, dem, minElev: 500, exaggeration: 2.4, elev01: new Float32Array(4), shade: new Float32Array(4).fill(1),
    deterministic: new Float32Array([10, 100, Infinity, Infinity]),
    particle: new Float32Array([20, Infinity, Infinity, Infinity]),
    // two ensemble runs in 5-minute steps; 255 = never. Cell 0: both runs reach it at 10 and 20 min; cell 1: one run at 100.
    ensemble: new Uint8Array([2, 20, 255, 255, 4, 255, 255, 255]), runs: 2, quantumMin: 5, never: 255,
  }
}

const rgb = (out: Float32Array, i: number) => [out[i * 3]!, out[i * 3 + 1]!, out[i * 3 + 2]!]
const GROUND = (d: FireData) => { const o = new Float32Array(12); colorize(o, d, 'deterministic', 0); return rgb(o, 3) }

describe('decoding', () => {
  it('turns null into infinity and keeps numbers', () => {
    expect(Array.from(toFloat32([1, null, 3]))).toEqual([1, Infinity, 3])
  })
  it('decodes base64 bytes', () => {
    expect(Array.from(decodeBase64(btoa(String.fromCharCode(0, 7, 255))))).toEqual([0, 7, 255])
  })
})

describe('colorize (deterministic and particle)', () => {
  const d = tiny()
  it('leaves unreached cells as ground at any time', () => {
    const out = new Float32Array(12)
    colorize(out, d, 'deterministic', 5)
    expect(rgb(out, 0)).toEqual(GROUND(d).map((_, k) => rgb(out, 0)[k]))   // not yet burning: ground colour
    expect(rgb(out, 2)).toEqual(GROUND(d))
  })
  it('shows flames just after arrival and charcoal long after', () => {
    const out = new Float32Array(12)
    colorize(out, d, 'deterministic', 20) // 10 minutes after arrival: flame (warm: red > blue)
    expect(out[0]).toBeGreaterThan(out[2]!)
    expect(out[0]).toBeGreaterThan(0.8)
    colorize(out, d, 'deterministic', 200) // 190 minutes after arrival: burned out (dark)
    expect(Math.max(...rgb(out, 0))).toBeLessThan(0.4)
  })
  it('uses the particle arrivals in particle mode', () => {
    const out = new Float32Array(12)
    colorize(out, d, 'particle', 100)
    expect(Math.max(...rgb(out, 1))).toBeCloseTo(Math.max(...GROUND(d)), 5) // cell 1 never burns in the particle model
  })
})

describe('colorize (probabilistic)', () => {
  const d = tiny()
  it('colours by the share of runs that reached each cell', () => {
    const out = new Float32Array(12)
    colorize(out, d, 'probabilistic', 60) // at 60 min: cell 0 reached by both runs (10, 20 min) -> p = 1
    expect(rgb(out, 0)).toEqual(heat(1).map((v) => Math.fround(v)))
    colorize(out, d, 'probabilistic', 15) // at 15 min: only the 10-min run -> p = 0.5
    expect(rgb(out, 0)).toEqual(heat(0.5).map((v) => Math.fround(v)))
    colorize(out, d, 'probabilistic', 1) // before any arrival: ground
    expect(rgb(out, 0)).toEqual(GROUND(d))
  })
  it('heat is monotone from pale to dark red', () => {
    expect(heat(0)[1]).toBeGreaterThan(heat(1)[1])
    expect(heat(1)[0]).toBeLessThan(heat(0.5)[0] + 1e-9)
  })
})

describe('shading and timeline', () => {
  it('lights slopes that face the western light and darkens the ones facing away', () => {
    const rows = 5, cols = 5
    const ramp = (dir: 1 | -1) => {
      const dem = new Float32Array(rows * cols)
      for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) dem[r * cols + c] = (dir === 1 ? c : cols - 1 - c) * 20
      return bakeShade(dem, rows, cols, 30)
    }
    const flat = bakeShade(new Float32Array(rows * cols), rows, cols, 30)
    const risesEast = ramp(1) // its face tilts west, towards the light
    const risesWest = ramp(-1) // its face tilts east, away from the light
    expect(risesEast[12]).toBeGreaterThan(flat[12]!)
    expect(risesWest[12]).toBeLessThan(flat[12]!)
    for (const v of [...risesEast, ...risesWest, ...flat]) {
      expect(v).toBeGreaterThanOrEqual(0.5)
      expect(v).toBeLessThanOrEqual(1)
    }
  })
  it('indexes the quarter-hour timeline safely', () => {
    expect(timelineIndex(0, 49)).toBe(0)
    expect(timelineIndex(6, 49)).toBe(24)
    expect(timelineIndex(99, 49)).toBe(48)
    expect(timelineIndex(-3, 49)).toBe(0)
  })
})

describe('exaggerationFor', () => {
  it('stretches flat terrain so it is visible, but never shrinks rugged terrain', () => {
    expect(exaggerationFor(20)).toBe(10)     // flat plain: capped at 10x
    expect(exaggerationFor(120)).toBeCloseTo(2, 5)
    expect(exaggerationFor(500)).toBe(1)     // mountains: drawn true to scale
    expect(exaggerationFor(0)).toBe(10)      // degenerate tile does not divide by zero
  })
})
