import { useCallback, useMemo, useSyncExternalStore } from 'react'
import type { Mode } from '../api/types'

/** Dashboard filters. Kept in the URL so every view is shareable and bookmarkable. */
export interface Filters {
  start: string
  end: string
  mode: Mode
  cutoff_time: string
  horizon_hours: number
}

export interface Bounds {
  minDate: string
  maxDate: string
  minHorizon: number
  maxHorizon: number
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/
const HHMM_RE = /^([01]\d|2[0-3]):[0-5]\d$/

/** Parse filters from a query string. Each invalid or missing value falls back to its default. */
export function parseFilters(search: string, defaults: Filters, bounds: Bounds): Filters {
  const q = new URLSearchParams(search)
  const inRange = (d: string | null) =>
    d !== null && DATE_RE.test(d) && d >= bounds.minDate && d <= bounds.maxDate

  let start = q.get('start')
  let end = q.get('end')
  start = inRange(start) ? start! : defaults.start
  end = inRange(end) ? end! : defaults.end
  if (start > end) {
    start = defaults.start
    end = defaults.end
  }

  const modeParam = q.get('mode')
  const mode: Mode = modeParam === 'cutoff' || modeParam === 'horizon' ? modeParam : defaults.mode

  const cutoff = q.get('cutoff_time')
  const cutoff_time = cutoff && HHMM_RE.test(cutoff) ? cutoff : defaults.cutoff_time

  const h = Number(q.get('horizon_hours'))
  const horizon_hours =
    Number.isInteger(h) && h >= bounds.minHorizon && h <= bounds.maxHorizon
      ? h
      : defaults.horizon_hours

  return { start, end, mode, cutoff_time, horizon_hours }
}

/** Serialise only the values that differ from the defaults, so the default view has a clean URL. */
export function serializeFilters(f: Filters, defaults: Filters): string {
  const q = new URLSearchParams()
  for (const key of Object.keys(f) as (keyof Filters)[]) {
    if (f[key] !== defaults[key]) q.set(key, String(f[key]))
  }
  const s = q.toString()
  return s ? `?${s}` : ''
}

// Minimal URL store: replaceState does not fire events, so notify subscribers ourselves.
const listeners = new Set<() => void>()
function subscribe(cb: () => void) {
  listeners.add(cb)
  window.addEventListener('popstate', cb)
  return () => {
    listeners.delete(cb)
    window.removeEventListener('popstate', cb)
  }
}
const getSearch = () => window.location.search

export function useUrlState(
  defaults: Filters | undefined,
  bounds: Bounds | undefined,
): [Filters | undefined, (patch: Partial<Filters>) => void] {
  const search = useSyncExternalStore(subscribe, getSearch)

  const filters = useMemo(
    () => (defaults && bounds ? parseFilters(search, defaults, bounds) : undefined),
    [search, defaults, bounds],
  )

  const update = useCallback(
    (patch: Partial<Filters>) => {
      if (!filters || !defaults) return
      const next = serializeFilters({ ...filters, ...patch }, defaults)
      window.history.replaceState(null, '', `${window.location.pathname}${next}`)
      listeners.forEach((cb) => cb())
    },
    [filters, defaults],
  )

  return [filters, update]
}
