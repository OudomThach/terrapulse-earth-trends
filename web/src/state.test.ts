import { describe, expect, it } from 'vitest'
import { CUSTOM, DEFAULTS, parseState, serializeState } from './state'

describe('URL state', () => {
  it('defaults produce a clean address', () => {
    expect(serializeState(DEFAULTS)).toBe('')
    expect(parseState('')).toEqual(DEFAULTS)
  })

  it('round-trips a non-default view', () => {
    const s = { ...DEFAULTS, view: 'risk' as const, riskTab: 'fire' as const, region: 'Hays, Kansas (USA)', horizon: 21 }
    expect(parseState(serializeState(s))).toEqual(s)
  })

  it('round-trips a detective investigation, including the question and window', () => {
    const s = { ...DEFAULTS, place: 'Greenland ice sheet', stage: 'evidence' as const, code: 'CLOUD_AMT', mapCode: 'CLOUD_AMT',
      start: 2002, end: 2025, question: 'hotter' }
    const back = parseState(serializeState(s))
    expect(back).toEqual(s)
  })

  it('keeps coordinates only for a custom place', () => {
    expect(serializeState({ ...DEFAULTS, place: 'Svalbard, Arctic', lat: 1, lon: 2 })).not.toContain('lat=')
    const custom = serializeState({ ...DEFAULTS, place: CUSTOM, lat: -33.9, lon: 151.2 })
    expect(custom).toContain('lat=-33.9')
    expect(parseState(custom)).toMatchObject({ place: CUSTOM, lat: -33.9, lon: 151.2 })
  })

  it('falls back to defaults for invalid or hostile input', () => {
    const s = parseState('?view=hack&stage=nope&risk=zzz&lat=abc&horizon=999&from=1900&to=3000&place=')
    expect(s.view).toBe('detective')
    expect(s.stage).toBe('suspects')
    expect(s.riskTab).toBe('forecast')
    expect(s.horizon).toBe(28) // clamped
    expect(s.lat).toBe(DEFAULTS.lat)
    expect(s.place).toBe(DEFAULTS.place)
  })

  it('rejects a window shorter than ten years', () => {
    const s = parseState('?from=2020&to=2025')
    expect([s.start, s.end]).toEqual([DEFAULTS.start, DEFAULTS.end])
  })

  it('knows whether the map variable was chosen explicitly by a link', () => {
    expect(parseState('?stage=world&var=T2M').mapFollows).toBe(true)
    const explicit = parseState('?stage=world&map=ALLSKY_SFC_SW_DWN')
    expect(explicit.mapFollows).toBe(false)
    expect(explicit.mapCode).toBe('ALLSKY_SFC_SW_DWN')
  })

  it('clamps latitude and longitude', () => {
    expect(parseState('?lat=500&lon=-999')).toMatchObject({ lat: 90, lon: -180 })
  })
})
