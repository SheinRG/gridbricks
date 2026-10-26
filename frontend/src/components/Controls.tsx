import type { Bounds, Filters } from '../hooks/useUrlState'

interface ControlsProps {
  filters: Filters
  bounds: Bounds
  onChange: (patch: Partial<Filters>) => void
}

const inputCls =
  'rounded-md border border-stone-300 bg-white px-2 py-1 text-sm text-stone-900 tabular-nums focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30'

export function Controls({ filters, bounds, onChange }: ControlsProps) {
  return (
    <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
      <fieldset className="flex items-end gap-2">
        <legend className="sr-only">Delivery days</legend>
        <label className="flex flex-col gap-1 text-xs text-stone-600">
          From (delivery day)
          <input
            type="date"
            className={inputCls}
            value={filters.start}
            min={bounds.minDate}
            max={bounds.maxDate}
            onChange={(e) => {
              const start = e.target.value
              if (!start) return
              onChange(start > filters.end ? { start, end: start } : { start })
            }}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-stone-600">
          To
          <input
            type="date"
            className={inputCls}
            value={filters.end}
            min={filters.start}
            max={bounds.maxDate}
            onChange={(e) => e.target.value && onChange({ end: e.target.value })}
          />
        </label>
      </fieldset>

      <div className="flex flex-col gap-1 text-xs text-stone-600">
        <span id="mode-label">Forecast selection</span>
        <div
          role="radiogroup"
          aria-labelledby="mode-label"
          className="inline-flex rounded-md bg-stone-200/70 p-0.5"
        >
          {(
            [
              ['cutoff', 'Trading cutoff'],
              ['horizon', 'Fixed horizon'],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={filters.mode === value}
              onClick={() => onChange({ mode: value })}
              className={`rounded px-3 py-1 text-sm transition ${
                filters.mode === value
                  ? 'bg-white font-medium text-stone-900 shadow-sm'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {filters.mode === 'cutoff' ? (
        <label className="flex flex-col gap-1 text-xs text-stone-600">
          Decision time on D-1 (UK)
          <input
            type="time"
            step={60}
            className={inputCls}
            value={filters.cutoff_time}
            onChange={(e) => e.target.value && onChange({ cutoff_time: e.target.value })}
          />
        </label>
      ) : (
        <label className="flex min-w-56 flex-col gap-1 text-xs text-stone-600">
          <span>
            Forecast made at least{' '}
            <strong className="tabular-nums text-stone-900">{filters.horizon_hours} h</strong> before delivery
          </span>
          <input
            type="range"
            min={bounds.minHorizon}
            max={bounds.maxHorizon}
            value={filters.horizon_hours}
            onChange={(e) => onChange({ horizon_hours: Number(e.target.value) })}
            className="accent-blue-600"
          />
        </label>
      )}
    </div>
  )
}
