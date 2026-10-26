import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Summary } from '../api/types'
import { KpiRow } from './KpiRow'

const summary: Summary = {
  n: 744,
  expected: 744,
  coverage_pct: 100,
  mae_mw: 1995.6,
  rmse_mw: 2498.8,
  bias_mw: 1728,
  p90_mw: 4183.9,
  p10_mw: -502.7,
  p50_mw: 1506.5,
  shortfall_buffer_mw: 4183.9,
  mean_actual_mw: 11285.5,
  nmae_pct: 17.7,
  max_over_forecast: null,
  max_under_forecast: null,
}

describe('KpiRow', () => {
  it('leads with the shortfall buffer phrased as a purchase decision', () => {
    render(<KpiRow summary={summary} />)
    expect(screen.getByText('Shortfall buffer (P90)')).toBeInTheDocument()
    expect(screen.getAllByText('4,184 MW').length).toBeGreaterThan(0)
    expect(screen.getByText(/above the forecast to cover wind shortfall in 90% of hours/)).toBeInTheDocument()
  })

  it('shows signed bias with its meaning, and the sample size', () => {
    render(<KpiRow summary={summary} />)
    expect(screen.getByText('+1,728 MW')).toBeInTheDocument()
    expect(screen.getByText('Forecasts ran high on average')).toBeInTheDocument()
    expect(screen.getByText('744 of 744 hours scored')).toBeInTheDocument()
  })

  it('renders n/a rather than zero when metrics are missing', () => {
    render(<KpiRow summary={{ ...summary, mae_mw: null, nmae_pct: null }} />)
    expect(screen.getByText('n/a')).toBeInTheDocument()
  })
})
