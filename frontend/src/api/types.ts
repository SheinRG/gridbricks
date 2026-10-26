// Mirrors backend/app/schemas.py. Times are UTC ISO 8601 strings; power values are MW.

export type Mode = 'cutoff' | 'horizon'

export interface DateRange {
  start: string
  end: string
}

export interface Meta {
  data_range: DateRange
  defaults: {
    start: string
    end: string
    mode: Mode
    cutoff_time: string
    horizon_hours: number
  }
  horizon_hours_min: number
  horizon_hours_max: number
  timezone: string
  ingested_at: string | null
  notes: string[]
}

export interface ParamsEcho {
  start: string
  end: string
  mode: Mode
  cutoff_time: string | null
  horizon_hours: number | null
}

export interface SeriesPoint {
  start_time: string
  actual_mw: number | null
  forecast_mw: number | null
  publish_time: string | null
  lead_time_hours: number | null
  /** forecast - actual; positive means wind fell short of forecast */
  error_mw: number | null
}

export interface SeriesResponse {
  params: ParamsEcho
  points: SeriesPoint[]
}

export interface ErrorStats {
  n: number
  mae_mw: number | null
  rmse_mw: number | null
  bias_mw: number | null
  p90_mw: number | null
}

export interface Extreme {
  start_time: string
  error_mw: number
  forecast_mw: number
  actual_mw: number
}

export interface Summary extends ErrorStats {
  expected: number
  coverage_pct: number | null
  p10_mw: number | null
  p50_mw: number | null
  shortfall_buffer_mw: number | null
  mean_actual_mw: number | null
  nmae_pct: number | null
  max_over_forecast: Extreme | null
  max_under_forecast: Extreme | null
}

export interface HourStats extends ErrorStats {
  hour: number
}

export interface LeadBucketStats extends ErrorStats {
  label: string
  lead_min_h: number
  lead_max_h: number
}

export interface DayStats extends ErrorStats {
  date: string
}

export interface Miss {
  start_time: string
  actual_mw: number
  forecast_mw: number
  error_mw: number
  publish_time: string
  lead_time_hours: number
}

export interface MetricsResponse {
  params: ParamsEcho
  summary: Summary
  by_hour: HourStats[]
  by_lead_bucket: LeadBucketStats[]
  by_day: DayStats[]
  worst_misses: Miss[]
}

export interface HorizonPoint extends ErrorStats {
  horizon_hours: number
  coverage_pct: number | null
  mean_lead_hours: number | null
}

export interface HorizonResponse {
  params: DateRange
  points: HorizonPoint[]
}
