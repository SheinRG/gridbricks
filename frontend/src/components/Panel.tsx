import type { ReactNode } from 'react'

interface QueryState {
  isPending: boolean
  isError: boolean
  error: Error | null
  isPlaceholderData?: boolean
  isFetching?: boolean
}

interface PanelProps {
  title: string
  subtitle?: ReactNode
  query: QueryState
  isEmpty?: boolean
  emptyMessage?: string
  /** Skeleton height while the first load is in flight. */
  height?: number
  actions?: ReactNode
  children: ReactNode
}

export function Skeleton({ height }: { height: number }) {
  return (
    <div
      className="w-full animate-pulse rounded-md bg-stone-200/70"
      style={{ height }}
      aria-label="Loading"
      role="status"
    />
  )
}

/** Card wrapper that gives every query a loading, error and empty state. */
export function Panel({
  title,
  subtitle,
  query,
  isEmpty,
  emptyMessage = 'No data for this selection.',
  height = 280,
  actions,
  children,
}: PanelProps) {
  const refreshing = query.isFetching && query.isPlaceholderData
  let body: ReactNode
  if (query.isPending) body = <Skeleton height={height} />
  else if (query.isError)
    body = (
      <div
        role="alert"
        className="flex items-center justify-center rounded-md border border-red-200 bg-red-50 px-4 text-sm text-red-800"
        style={{ minHeight: height / 2 }}
      >
        Could not load: {query.error?.message ?? 'unknown error'}
      </div>
    )
  else if (isEmpty)
    body = (
      <div
        className="flex items-center justify-center rounded-md bg-stone-50 text-sm text-stone-500"
        style={{ minHeight: height / 2 }}
      >
        {emptyMessage}
      </div>
    )
  else body = children

  return (
    <section className="rounded-lg bg-[#fcfcfb] p-4 shadow-sm ring-1 ring-black/10">
      <header className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-stone-900">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-stone-500">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-3">
          {refreshing && <span className="text-xs text-stone-400">Updating...</span>}
          {actions}
        </div>
      </header>
      <div className={refreshing ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
        {body}
      </div>
    </section>
  )
}
