import ReactEChartsCore from 'echarts-for-react/lib/core'
import { memo, useMemo } from 'react'
import type { HorizonPoint } from '../api/types'
import { colors } from '../lib/colors'
import { baseText, echarts, lineKey, tooltipBase, valueAxisMW } from '../lib/echarts'
import { formatHours, formatMW, formatPct, formatSignedMW } from '../lib/format'

interface HorizonChartProps {
  points: HorizonPoint[]
  /** Where the current selection sits on the x axis, in hours, and how to label it. */
  marker: { hours: number; label: string } | null
}

/** How accuracy decays as the forecast is made further ahead of delivery. */
function HorizonChartImpl({ points, marker }: HorizonChartProps) {
  const option = useMemo(
    () => ({
      animation: false,
      textStyle: baseText,
      legend: {
        top: 0,
        right: 0,
        itemWidth: 14,
        itemHeight: 2,
        textStyle: { ...baseText, color: colors.inkSecondary },
        data: [
          { name: 'Typical miss (MAE)', icon: 'rect' },
          { name: 'P90 error (shortfall buffer)', icon: 'rect' },
        ],
      },
      grid: { left: 56, right: 24, top: 36, bottom: 40 },
      xAxis: {
        type: 'value',
        min: 0,
        max: 48,
        interval: 6,
        name: 'Hours between forecast and delivery (H)',
        nameLocation: 'middle',
        nameGap: 26,
        nameTextStyle: { ...baseText, color: colors.muted },
        axisLabel: { ...baseText, color: colors.muted, formatter: '{value} h' },
        axisLine: { lineStyle: { color: colors.axis } },
        splitLine: { show: false },
      },
      yAxis: { ...valueAxisMW, scale: true },
      tooltip: {
        ...tooltipBase,
        trigger: 'axis',
        formatter: (params: { dataIndex: number }[]) => {
          const p = points[params[0].dataIndex]
          return [
            `<b>H = ${p.horizon_hours} h</b> <span style="color:${colors.muted}">(actual lead averages ${formatHours(p.mean_lead_hours)})</span>`,
            `${lineKey(colors.actual)}<b>${formatMW(p.mae_mw)}</b> typical miss (MAE)`,
            `${lineKey(colors.forecast)}<b>${formatSignedMW(p.p90_mw)}</b> P90 error`,
            `<span style="color:${colors.muted}">${p.n} hours scored, coverage ${formatPct(p.coverage_pct, 0)}</span>`,
          ].join('<br/>')
        },
      },
      series: [
        {
          name: 'Typical miss (MAE)',
          type: 'line',
          data: points.map((p) => [p.horizon_hours, p.mae_mw]),
          showSymbol: false,
          lineStyle: { width: 2, color: colors.actual },
          itemStyle: { color: colors.actual },
          markLine: marker
            ? {
                silent: true,
                symbol: 'none',
                lineStyle: { color: colors.ink, type: 'dashed', width: 1 },
                label: {
                  ...baseText,
                  color: colors.ink,
                  position: 'insideEndTop',
                  formatter: marker.label,
                },
                data: [{ xAxis: marker.hours }],
              }
            : undefined,
        },
        {
          name: 'P90 error (shortfall buffer)',
          type: 'line',
          data: points.map((p) => [p.horizon_hours, p.p90_mw]),
          showSymbol: false,
          lineStyle: { width: 2, color: colors.forecast },
          itemStyle: { color: colors.forecast },
        },
      ],
    }),
    [points, marker],
  )

  return (
    <ReactEChartsCore echarts={echarts} option={option} notMerge style={{ height: 300 }} />
  )
}

export const HorizonChart = memo(HorizonChartImpl)
