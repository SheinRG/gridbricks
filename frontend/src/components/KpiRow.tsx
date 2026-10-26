import type { ReactNode } from 'react'
import type { Summary } from '../api/types'
import { formatMW, formatPct, formatSignedMW } from '../lib/format'

interface TileProps {
  label: string
  value: string
  detail?: ReactNode
  help: string
  emphasis?: boolean
}

function Tile({ label, value, detail, help, emphasis }: TileProps) {
  return (
    <div
      className={`group relative rounded-lg p-4 ring-1 ${
        emphasis ? 'bg-red-50/60 ring-red-200 sm:col-span-2' : 'bg-[#fcfcfb] ring-black/10'
      }`}
    >
      <div className="flex items-center gap-1.5 text-xs font-medium text-stone-600">
        {label}
        <button
          type="button"
          aria-label={`About ${label}: ${help}`}
          className="flex h-4 w-4 items-center justify-center rounded-full border border-stone-300 text-[10px] leading-none text-stone-500 hover:border-stone-500"
        >
          i
        </button>
      </div>
      <div
        className={`mt-1 font-semibold tracking-tight text-stone-900 ${emphasis ? 'text-3xl' : 'text-2xl'}`}
      >
        {value}
      </div>
      {detail && <div className="mt-1 text-xs text-stone-500">{detail}</div>}
      <div
        role="tooltip"
        className="pointer-events-none absolute left-3 top-full z-20 mt-1 hidden w-64 rounded-md bg-stone-900 px-3 py-2 text-xs leading-snug text-white shadow-lg group-focus-within:block group-hover:block"
      >
        {help}
      </div>
    </div>
  )
}

export function KpiRow({ summary }: { summary: Summary }) {
  const s = summary
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      <Tile
        emphasis
        label="Shortfall buffer (P90)"
        value={formatMW(s.shortfall_buffer_mw)}
        detail={
          <>
            Buy about <strong className="text-stone-800">{formatMW(s.shortfall_buffer_mw)}</strong>{' '}
            above the forecast to cover wind shortfall in 90% of hours.
          </>
        }
        help="90% of the time, actual wind came in no more than this far below the forecast you had at decision time. Procuring this much extra would have covered the shortfall in 9 out of 10 hours."
      />
      <Tile
        label="Typical miss (MAE)"
        value={formatMW(s.mae_mw)}
        detail={`${formatPct(s.nmae_pct)} of mean wind output (${formatMW(s.mean_actual_mw)})`}
        help="Mean absolute error: on average, how far the forecast was from what was generated, in either direction."
      />
      <Tile
        label="RMSE"
        value={formatMW(s.rmse_mw)}
        detail="Weights large misses more heavily"
        help="Root mean squared error. Like MAE, but big misses count for more, so it rises when there are occasional large errors."
      />
      <Tile
        label="Bias"
        value={formatSignedMW(s.bias_mw)}
        detail={
          s.bias_mw == null
            ? undefined
            : s.bias_mw > 0
              ? 'Forecasts ran high on average'
              : 'Forecasts ran low on average'
        }
        help="Average of forecast minus actual. Positive means the forecast was too high on average, so wind under-delivered and you would have been short."
      />
      <Tile
        label="Coverage"
        value={formatPct(s.coverage_pct, 0)}
        detail={`${s.n.toLocaleString('en-GB')} of ${s.expected.toLocaleString('en-GB')} hours scored`}
        help="Share of hourly delivery slots where both a forecast and an actual value exist. Every metric on this page is computed over these hours only."
      />
    </div>
  )
}
