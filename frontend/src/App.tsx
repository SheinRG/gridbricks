import { useMemo, useState } from 'react'
import { useHorizon, useMeta, useMetrics, useSeries } from './api/hooks'
import { Controls } from './components/Controls'
import { ErrorHistogram } from './components/ErrorHistogram'
import { HorizonChart } from './components/HorizonChart'
import { HourChart } from './components/HourChart'
import { KpiRow } from './components/KpiRow'
import { MainChart } from './components/MainChart'
import { Methodology } from './components/Methodology'
import { Panel, Skeleton } from './components/Panel'
import { WorstMisses } from './components/WorstMisses'
import { useDebouncedValue } from './hooks/useDebouncedValue'
import { type Bounds, type Filters, useUrlState } from './hooks/useUrlState'
import { formatDate } from './lib/format'

export default function App() {
  const meta = useMeta()

  const defaults = useMemo<Filters | undefined>(() => meta.data?.defaults, [meta.data])
  const bounds = useMemo<Bounds | undefined>(
    () =>
      meta.data && {
        minDate: meta.data.data_range.start,
        maxDate: meta.data.data_range.end,
        minHorizon: meta.data.horizon_hours_min,
        maxHorizon: meta.data.horizon_hours_max,
      },
    [meta.data],
  )
  const [filters, setFilters] = useUrlState(defaults, bounds)
  // Typing a time or picking dates should not fire a request per keystroke.
  const queryFilters = useDebouncedValue(filters, 300)

  const series = useSeries(queryFilters)
  const metrics = useMetrics(queryFilters)
  const horizon = useHorizon(queryFilters?.start, queryFilters?.end)
  const [showFloor, setShowFloor] = useState(false)

  const points = series.data?.points
  const summary = metrics.data?.summary

  const horizonMarker = useMemo(() => {
    if (!queryFilters) return null
    if (queryFilters.mode === 'horizon')
      return { hours: queryFilters.horizon_hours, label: `Selected H = ${queryFilters.horizon_hours} h` }
    const leads = (points ?? []).flatMap((p) => (p.lead_time_hours == null ? [] : [p.lead_time_hours]))
    if (leads.length === 0) return null
    const mean = leads.reduce((a, b) => a + b, 0) / leads.length
    return {
      hours: mean,
      label: `${queryFilters.cutoff_time} cutoff: avg lead ${mean.toFixed(0)} h`,
    }
  }, [queryFilters, points])

  const selectionText =
    filters &&
    `${formatDate(filters.start)} to ${formatDate(filters.end)}, ${
      filters.mode === 'cutoff'
        ? `forecast available at ${filters.cutoff_time} UK the day before`
        : `forecast made at least ${filters.horizon_hours} h ahead`
    }`

  return (
    <div className="min-h-screen bg-[#f9f9f7] text-stone-900">
      <header className="border-b border-black/10 bg-[#fcfcfb]">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">UK Wind Forecast Monitor</h1>
              <p className="mt-0.5 text-sm text-stone-600">
                The wind forecast you had at day-ahead decision time, against what was actually
                generated. GB national, January 2026 decisions.
              </p>
            </div>
            {filters && bounds ? (
              <Controls filters={filters} bounds={bounds} onChange={setFilters} />
            ) : meta.isError ? null : (
              <div className="w-96">
                <Skeleton height={44} />
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-5 sm:px-6">
        {meta.isError ? (
          <div role="alert" className="rounded-lg bg-red-50 p-4 text-sm text-red-800 ring-1 ring-red-200">
            Could not reach the API: {meta.error.message}
          </div>
        ) : (
          <>
            <p className="text-xs text-stone-500">
              {selectionText ?? ' '}
              <span className="ml-2 rounded bg-stone-200/70 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-stone-600">
                Times in UK time
              </span>
            </p>

            {metrics.isError ? (
              <div role="alert" className="rounded-lg bg-red-50 p-4 text-sm text-red-800 ring-1 ring-red-200">
                Could not load metrics: {metrics.error.message}
              </div>
            ) : summary ? (
              summary.n === 0 ? (
                <div className="rounded-lg bg-stone-50 p-4 text-sm text-stone-600 ring-1 ring-black/10">
                  No hours could be scored for this selection.
                </div>
              ) : (
                <div className={metrics.isPlaceholderData ? 'opacity-60 transition-opacity' : ''}>
                  <KpiRow summary={summary} />
                </div>
              )
            ) : (
              <Skeleton height={112} />
            )}

            <Panel
              title="Actual wind generation vs the forecast you had"
              subtitle="Half-hourly actuals, hourly forecasts. Bottom strip: forecast minus actual; red bars are shortfalls. Drag or scroll to zoom."
              query={series}
              isEmpty={points?.length === 0}
              height={420}
              actions={
                <label
                  className="flex items-center gap-1.5 text-xs text-stone-600"
                  title="Forecast minus the P90 shortfall buffer computed over the same period. This uses hindsight, so treat it as a backtest, not a live rule."
                >
                  <input
                    type="checkbox"
                    checked={showFloor}
                    onChange={(e) => setShowFloor(e.target.checked)}
                    disabled={summary?.shortfall_buffer_mw == null}
                  />
                  Show P90 wind floor (in-sample backtest)
                </label>
              }
            >
              {points && (
                <MainChart
                  points={points}
                  floorBufferMw={showFloor ? summary?.shortfall_buffer_mw : null}
                />
              )}
            </Panel>

            <div className="grid gap-4 lg:grid-cols-2">
              <Panel
                title="How big are the misses?"
                subtitle="Distribution of hourly error, with P10, P50 and P90 marked. Red is shortfall."
                query={series}
                isEmpty={summary?.n === 0}
              >
                {points && summary && <ErrorHistogram points={points} summary={summary} />}
              </Panel>
              <Panel
                title="When in the day are forecasts worst?"
                subtitle="Typical miss and bias by delivery hour."
                query={metrics}
                isEmpty={summary?.n === 0}
              >
                {metrics.data && <HourChart byHour={metrics.data.by_hour} />}
              </Panel>
            </div>

            <Panel
              title="Accuracy vs how far ahead the forecast was made"
              subtitle="Fixed horizon view over the selected days: for each H, the latest forecast made at least H hours before delivery."
              query={horizon}
              isEmpty={horizon.data?.points.length === 0}
              height={300}
            >
              {horizon.data && <HorizonChart points={horizon.data.points} marker={horizonMarker} />}
            </Panel>

            <Panel
              title="Worst misses"
              subtitle="Ten hours with the largest absolute error in the selection."
              query={metrics}
              isEmpty={metrics.data?.worst_misses.length === 0}
              height={200}
            >
              {metrics.data && <WorstMisses misses={metrics.data.worst_misses} />}
            </Panel>

            <Methodology />
          </>
        )}
      </main>
    </div>
  )
}
