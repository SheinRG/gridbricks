export interface Bin {
  lo: number
  hi: number
  count: number
}

/** Fixed-width bins aligned to multiples of `width`, covering every value. */
export function histogram(values: number[], width: number): Bin[] {
  if (values.length === 0) return []
  const lo = Math.floor(Math.min(...values) / width) * width
  const hi = Math.floor(Math.max(...values) / width) * width
  const bins: Bin[] = []
  for (let b = lo; b <= hi; b += width) bins.push({ lo: b, hi: b + width, count: 0 })
  for (const v of values) bins[Math.floor((v - lo) / width)].count++
  return bins
}
