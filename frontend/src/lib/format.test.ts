import { describe, expect, it } from 'vitest'
import { formatDate, formatMW, formatPct, formatSignedMW, formatUkAxis, formatUkDateTime } from './format'
import { histogram } from './histogram'

describe('number formatting', () => {
  it('formats MW with thousands separators and no decimals', () => {
    expect(formatMW(4183.9)).toBe('4,184 MW')
    expect(formatMW(null)).toBe('n/a')
  })

  it('always shows the sign of an error', () => {
    expect(formatSignedMW(1728)).toBe('+1,728 MW')
    expect(formatSignedMW(-3967)).toBe('−3,967 MW')
    expect(formatSignedMW(0.2)).toBe('0 MW')
  })

  it('formats percentages', () => {
    expect(formatPct(17.66)).toBe('17.7%')
    expect(formatPct(undefined)).toBe('n/a')
  })
})

describe('UK time formatting', () => {
  it('shows GMT times unchanged in winter', () => {
    expect(formatUkDateTime('2026-01-10T09:30:00Z')).toBe('Sat 10 Jan, 09:30')
  })

  it('shifts to BST in summer', () => {
    expect(formatUkDateTime('2026-07-01T09:30:00Z')).toBe('Wed 1 Jul, 10:30')
  })

  it('labels UK midnight with the date on axes', () => {
    expect(formatUkAxis(Date.parse('2026-01-10T00:00:00Z'))).toBe('10 Jan')
    expect(formatUkAxis(Date.parse('2026-01-10T06:00:00Z'))).toBe('06:00')
  })

  it('formats calendar dates without a timezone shift', () => {
    expect(formatDate('2026-02-01')).toBe('1 Feb 2026')
  })
})

describe('histogram', () => {
  it('bins values into fixed-width buckets aligned to the width', () => {
    const bins = histogram([-600, -100, 0, 499, 500, 1200], 500)
    expect(bins.map((b) => [b.lo, b.count])).toEqual([
      [-1000, 1],
      [-500, 1],
      [0, 2],
      [500, 1],
      [1000, 1],
    ])
  })

  it('returns no bins for no data', () => {
    expect(histogram([], 500)).toEqual([])
  })
})
