import type { Filters } from '../hooks/useUrlState'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type FastApiDetail = string | { msg: string; loc?: (string | number)[] }[]

/** Turn FastAPI's `detail` (a string, or a list of field errors) into one readable line. */
export function describeDetail(detail: FastApiDetail | undefined, fallback: string): string {
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  return detail
    .map((d) => {
      const field = d.loc?.filter((part) => part !== 'query').join('.')
      return field ? `${field}: ${d.msg}` : d.msg
    })
    .join('; ')
}

export async function apiGet<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const qs = params
    ? '?' + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString()
    : ''
  const res = await fetch(`/api/v1${path}${qs}`)
  if (!res.ok) {
    let detail: FastApiDetail | undefined
    try {
      detail = ((await res.json()) as { detail?: FastApiDetail }).detail
    } catch {
      // Non-JSON error body (for example a proxy error page).
    }
    throw new ApiError(res.status, describeDetail(detail, `Request failed (HTTP ${res.status})`))
  }
  return (await res.json()) as T
}

/** Only send the parameter the selected mode uses, so cache keys stay minimal. */
export function filterParams(f: Filters): Record<string, string | number> {
  const base = { start: f.start, end: f.end, mode: f.mode }
  return f.mode === 'cutoff'
    ? { ...base, cutoff_time: f.cutoff_time }
    : { ...base, horizon_hours: f.horizon_hours }
}
