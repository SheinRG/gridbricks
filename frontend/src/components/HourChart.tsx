import ReactEChartsCore from 'echarts-for-react/lib/core'
import { memo, useMemo } from 'react'
import type { HourStats } from '../api/types'
import { colors } from '../lib/colors'
import { baseText, echarts, lineKey, tooltipBase, valueAxisMW } from '../lib/echarts'
import { formatMW, formatSignedMW } from '../lib/format'

/** Typical miss and bias by UK hour of day: when in the day is the forecast least reliable? */
function HourChartImpl({ byHour }: { byHour: HourStats[] }) {
  const option = useMemo(
    () => ({
      animation: false,
      textStyle: baseText,
      legend: {
        top: 0,
        right: 0,
        itemWidth: 12,
        itemHeight: 8,
        textStyle: { ...baseText, color: colors.inkSecondary },
      },
      grid: { left: 56, right: 16, top: 32, bottom: 40 },
      xAxis: {
        type: 'category',
        data: byHour.map((h) => String(h.hour).padStart(2, '0')),
        name: 'Hour of day (UK)',
        nameLocation: 'middle',
        nameGap: 26,
        nameTextStyle: { ...baseText, color: colors.muted },
        axisLabel: { ...baseText, color: colors.muted, interval: 2 },
        axisLine: { lineStyle: { color: colors.axis } },
        axisTick: { show: false },
      },
      yAxis: valueAxisMW,
      tooltip: {
        ...tooltipBase,
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: { dataIndex: number }[]) => {
          const h = byHour[params[0].dataIndex]
          return [
            `<b>${String(h.hour).padStart(2, '0')}:00 UK</b> <span style="color:${colors.muted}">(${h.n} hours)</span>`,
            `${lineKey(colors.actual)}<b>${formatMW(h.mae_mw)}</b> typical miss (MAE)`,
            `${lineKey(colors.forecast)}<b>${formatSignedMW(h.bias_mw)}</b> bias`,
            `<span style="color:${colors.muted}">P90 error ${formatSignedMW(h.p90_mw)}</span>`,
          ].join('<br/>')
        },
      },
      series: [
        {
          name: 'Typical miss (MAE)',
          type: 'bar',
          data: byHour.map((h) => h.mae_mw),
          itemStyle: { color: colors.actual, borderRadius: [3, 3, 0, 0] },
          barGap: '10%',
        },
        {
          name: 'Bias',
          type: 'bar',
          data: byHour.map((h) => h.bias_mw),
          itemStyle: { color: colors.forecast, borderRadius: [3, 3, 0, 0] },
        },
      ],
    }),
    [byHour],
  )

  return (
    <ReactEChartsCore echarts={echarts} option={option} notMerge style={{ height: 280 }} />
  )
}

export const HourChart = memo(HourChartImpl)
