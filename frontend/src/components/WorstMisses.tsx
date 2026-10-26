import type { Miss } from '../api/types'
import { formatHours, formatMW, formatSignedMW, formatUkDateTime, formatUkShort } from '../lib/format'

export function WorstMisses({ misses }: { misses: Miss[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm tabular-nums">
        <thead>
          <tr className="border-b border-stone-200 text-left text-xs text-stone-500">
            <th className="py-2 pr-4 font-medium">Delivery hour (UK)</th>
            <th className="py-2 pr-4 text-right font-medium">Forecast</th>
            <th className="py-2 pr-4 text-right font-medium">Actual</th>
            <th className="py-2 pr-4 text-right font-medium">Error</th>
            <th className="py-2 pr-4 font-medium">Forecast published (UK)</th>
            <th className="py-2 text-right font-medium">Lead</th>
          </tr>
        </thead>
        <tbody>
          {misses.map((m) => (
            <tr key={m.start_time} className="border-b border-stone-100 last:border-0">
              <td className="py-1.5 pr-4 text-stone-900">{formatUkDateTime(m.start_time)}</td>
              <td className="py-1.5 pr-4 text-right">{formatMW(m.forecast_mw)}</td>
              <td className="py-1.5 pr-4 text-right">{formatMW(m.actual_mw)}</td>
              <td
                className={`py-1.5 pr-4 text-right font-medium ${m.error_mw > 0 ? 'text-red-700' : 'text-stone-600'}`}
              >
                {formatSignedMW(m.error_mw)}
                <span className="ml-1 text-xs font-normal">
                  {m.error_mw > 0 ? 'shortfall' : 'surplus'}
                </span>
              </td>
              <td className="py-1.5 pr-4 text-stone-600">{formatUkShort(m.publish_time)}</td>
              <td className="py-1.5 text-right text-stone-600">{formatHours(m.lead_time_hours)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
