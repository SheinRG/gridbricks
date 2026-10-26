export const UK_TZ = 'Europe/London'
const NA = 'n/a'

const mwFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })

/** 4183.9 -> "4,184 MW" */
export function formatMW(v: number | null | undefined): string {
  return v == null ? NA : `${mwFmt.format(v)} MW`
}

/** 1728 -> "+1,728 MW"; signs make the direction of an error explicit. */
export function formatSignedMW(v: number | null | undefined): string {
  if (v == null) return NA
  const rounded = Math.round(v)
  const sign = rounded > 0 ? '+' : rounded < 0 ? '−' : ''
  return `${sign}${mwFmt.format(Math.abs(rounded))} MW`
}

export function formatPct(v: number | null | undefined, digits = 1): string {
  return v == null ? NA : `${v.toFixed(digits)}%`
}

export function formatHours(v: number | null | undefined): string {
  return v == null ? NA : `${v.toFixed(1)} h`
}

const dateTimeFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: UK_TZ,
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const shortFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: UK_TZ,
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const dayFmt = new Intl.DateTimeFormat('en-GB', { timeZone: UK_TZ, day: 'numeric', month: 'short' })
const timeFmt = new Intl.DateTimeFormat('en-GB', {
  timeZone: UK_TZ,
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

type TimeInput = string | number | Date | null | undefined
const toDate = (t: Exclude<TimeInput, null | undefined>) => (t instanceof Date ? t : new Date(t))

/** UTC ISO -> "Sat 10 Jan, 09:30" in UK time. */
export function formatUkDateTime(t: TimeInput): string {
  return t == null ? NA : dateTimeFmt.format(toDate(t))
}

/** UTC ISO -> "9 Jan, 09:30" in UK time. */
export function formatUkShort(t: TimeInput): string {
  return t == null ? NA : shortFmt.format(toDate(t))
}

/** Axis label: "10 Jan" at UK midnight, otherwise "06:00". */
export function formatUkAxis(t: TimeInput): string {
  if (t == null) return ''
  const d = toDate(t)
  const hhmm = timeFmt.format(d)
  return hhmm === '00:00' ? dayFmt.format(d) : hhmm
}

/** "2026-01-02" -> "2 Jan 2026" (a calendar date, no timezone shift). */
export function formatDate(isoDate: string): string {
  const [y, m, d] = isoDate.split('-').map(Number)
  return new Intl.DateTimeFormat('en-GB', {
    timeZone: 'UTC',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(Date.UTC(y, m - 1, d)))
}
