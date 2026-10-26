// Register only the ECharts pieces we use, to keep the bundle lean.
import { BarChart, LineChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { colors } from './colors'

echarts.use([
  BarChart,
  LineChart,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
  CanvasRenderer,
])

export { echarts }

/** Shared chrome: recessive axes and gridlines, system font, MW-labelled value axis. */
export const baseText = {
  fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
  color: colors.inkSecondary,
  fontSize: 11,
}

export const valueAxisMW = {
  type: 'value' as const,
  name: 'MW',
  nameTextStyle: { ...baseText, color: colors.muted },
  axisLabel: { ...baseText, color: colors.muted },
  splitLine: { lineStyle: { color: colors.grid } },
  axisLine: { show: false },
}

export const tooltipBase = {
  backgroundColor: '#ffffff',
  borderColor: 'rgba(11,11,11,0.10)',
  textStyle: { ...baseText, color: colors.ink, fontSize: 12 },
  extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 6px;',
}

/** A short stroke of the series colour, used as the key in tooltip rows. */
export function lineKey(color: string): string {
  return `<span style="display:inline-block;width:10px;height:2px;background:${color};vertical-align:middle;margin-right:6px"></span>`
}
