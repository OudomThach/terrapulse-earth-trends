import { describe, expect, it } from 'vitest'
import { arrow, clamp, directionClass, fixed, MINUS, plainP, pText, signed, strengthDots } from './format'

describe('signed', () => {
  it('always shows a sign and uses a real minus', () => {
    expect(signed(1.234)).toBe('+1.23')
    expect(signed(-0.4, 1)).toBe(`${MINUS}0.4`)
    expect(signed(0, 2)).toBe('+0.00')
  })
  it('handles missing and non-finite values', () => {
    expect(signed(null)).toBe('n/a')
    expect(signed(undefined)).toBe('n/a')
    expect(signed(Number.NaN)).toBe('n/a')
    expect(signed(Number.POSITIVE_INFINITY)).toBe('n/a')
  })
  it('adds thousands separators', () => expect(signed(12345.6, 1)).toBe('+12,345.6'))
})

describe('plain-language probability', () => {
  it('describes tiny and ordinary p-values', () => {
    expect(plainP(0.0004)).toBe('less than 1 time in 1,000')
    expect(plainP(0.003)).toBe('about 3 times in 1,000')
    expect(plainP(0.039)).toBe('about 4 times in 100')
    expect(plainP(0.999)).toBe('almost every time')
  })
  it('formats p for display', () => {
    expect(pText(0.0002)).toBe('p < 0.001')
    expect(pText(0.0391)).toBe('p = 0.039')
    expect(pText(null)).toBe('n/a')
  })
})

describe('evidence meter and direction helpers', () => {
  it('maps p to dots without relying on colour', () => {
    expect([0.001, 0.03, 0.08, 0.4].map(strengthDots)).toEqual(['●●●', '●●○', '●○○', '○○○'])
  })
  it('maps direction to arrow and class', () => {
    expect(arrow('rising')).toBe('▲')
    expect(arrow('falling')).toBe('▼')
    expect(directionClass('rising')).toBe('rise')
    expect(directionClass('falling')).toBe('fall')
    expect(directionClass('flat')).toBe('flat')
  })
})

describe('numbers', () => {
  it('clamps', () => {
    expect(clamp(5, 0, 3)).toBe(3)
    expect(clamp(-1, 0, 3)).toBe(0)
    expect(clamp(2, 0, 3)).toBe(2)
  })
  it('fixes decimals with grouping', () => expect(fixed(1234.5678, 2)).toBe('1,234.57'))
})
