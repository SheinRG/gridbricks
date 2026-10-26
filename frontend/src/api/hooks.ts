import { keepPreviousData, useQuery } from '@tanstack/react-query'
import type { Filters } from '../hooks/useUrlState'
import { apiGet, filterParams } from './client'
import type { HorizonResponse, Meta, MetricsResponse, SeriesResponse } from './types'

export function useMeta() {
  return useQuery({ queryKey: ['meta'], queryFn: () => apiGet<Meta>('/meta') })
}

export function useSeries(filters: Filters | undefined) {
  return useQuery({
    queryKey: ['series', filters && filterParams(filters)],
    queryFn: () => apiGet<SeriesResponse>('/series', filterParams(filters!)),
    enabled: !!filters,
    placeholderData: keepPreviousData,
  })
}

export function useMetrics(filters: Filters | undefined) {
  return useQuery({
    queryKey: ['metrics', filters && filterParams(filters)],
    queryFn: () => apiGet<MetricsResponse>('/metrics', filterParams(filters!)),
    enabled: !!filters,
    placeholderData: keepPreviousData,
  })
}

export function useHorizon(start: string | undefined, end: string | undefined) {
  return useQuery({
    queryKey: ['accuracy-by-horizon', start, end],
    queryFn: () => apiGet<HorizonResponse>('/accuracy-by-horizon', { start: start!, end: end! }),
    enabled: !!start && !!end,
    placeholderData: keepPreviousData,
  })
}
