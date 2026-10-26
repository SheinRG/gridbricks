// Chart palette (dataviz reference instance, light mode). Validated slots, used by role.
export const colors = {
  actual: '#2a78d6', // categorical slot 1 (blue)
  forecast: '#eb6834', // categorical slot 2 (orange)
  // Error polarity: shortfall (forecast too high) is the costly direction and is always red;
  // surplus is deliberately quiet so red stays the only alarm on the page.
  shortfall: '#e34948',
  surplus: '#a8a7a1',
  floor: '#6250d6', // violet: P90 wind floor overlay
  ink: '#0b0b0b',
  inkSecondary: '#52514e',
  muted: '#898781',
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  surface: '#fcfcfb',
} as const
