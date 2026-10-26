import { describe, expect, it } from 'vitest'
import { type Bounds, type Filters, parseFilters, serializeFilters } from './useUrlState'

const defaults: Filters = {
  start: '2026-01-02',
  end: '2026-02-01',
  mode: 'cutoff',
  cutoff_time: '09:50',
  horizon_hours: 24,
}
const bounds: Bounds = { minDate: '2026-01-02', maxDate: '2026-02-01', minHorizon: 1, maxHorizon: 48 }

describe('parseFilters', () => {
  it('returns defaults for an empty query string', () => {
    expect(parseFilters('', defaults, bounds)).toEqual(defaults)
  })

  it('reads valid values', () => {
    const f = parseFilters(
      '?start=2026-01-10&end=2026-01-12&mode=horizon&cutoff_time=09:20&horizon_hours=6',
      defaults,
      bounds,
    )
    expect(f).toEqual({
      start: '2026-01-10',
      end: '2026-01-12',
      mode: 'horizon',
      cutoff_time: '09:20',
      horizon_hours: 6,
    })
  })

  it('falls back per field on invalid values', () => {
    const f = parseFilters(
      '?start=2025-12-01&end=nope&mode=sideways&cutoff_time=25:00&horizon_hours=99',
      defaults,
      bounds,
    )
    expect(f).toEqual(defaults)
  })

  it('resets an inverted date range to the defaults', () => {
    const f = parseFilters('?start=2026-01-20&end=2026-01-10', defaults, bounds)
    expect([f.start, f.end]).toEqual([defaults.start, defaults.end])
  })

  it('rejects non-integer horizons', () => {
    expect(parseFilters('?horizon_hours=2.5', defaults, bounds).horizon_hours).toBe(24)
  })
})

describe('serializeFilters', () => {
  it('omits defaults and round-trips through parseFilters', () => {
    expect(serializeFilters(defaults, defaults)).toBe('')
    const f: Filters = { ...defaults, mode: 'horizon', horizon_hours: 6 }
    const qs = serializeFilters(f, defaults)
    expect(qs).toBe('?mode=horizon&horizon_hours=6')
    expect(parseFilters(qs, defaults, bounds)).toEqual(f)
  })
})
