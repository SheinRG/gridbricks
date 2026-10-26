import ReactEChartsCore from 'echarts-for-react/lib/core'
import { memo, useMemo } from 'react'
import type { SeriesPoint, Summary } from '../api/types'
import { colors } from '../lib/colors'
import { baseText, echarts, tooltipBase } from '../lib/echarts'
import { formatSignedMW } from '../lib/format'
import { type Bin, histogram } from '../lib/histogram'

const BIN_MW = 500

function ErrorHistogramImpl({ points, summary }: { points: SeriesPoint[]; summary: Summary }) {
  const option = useMemo(() => {
    const errors = points.flatMap((p) => (p.error_mw == null ? [] : [p.error_mw]))
    const bins = histogram(errors, BIN_MW)
    const marks = [
      { name: 'P10', value: summary.p10_mw },
      { name: 'P50', value: summary.p50_mw },
      { name: 'P90', value: summary.p90_mw },
    ].filter((m): m is { name: string; value: number } => m.value != null)

    return {
      animation: false,
      textStyle: baseText,
      grid: { left: 44, right: 16, top: 28, bottom: 40 },
      xAxis: {
        type: 'value',
        name: 'Forecast minus actual (MW)',
        nameLocation: 'middle',
        nameGap: 26,
        nameTextStyle: { ...baseText, color: colors.muted },
        axisLabel: { ...baseText, color: colors.muted, formatter: (v: number) => formatSignedMW(v).replace(' MW', '') },
        axisLine: { lineStyle: { color: colors.axis } },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        name: 'Hours',
        nameTextStyle: { ...baseText, color: colors.muted },
        axisLabel: { ...baseText, color: colors.muted },
        splitLine: { lineStyle: { color: colors.grid } },
      },
      tooltip: {
        ...tooltipBase,
        trigger: 'item',
        formatter: (p: { data: { bin: Bin } }) =>
          `<b>${p.data.bin.count} hours</b><br/>error ${formatSignedMW(p.data.bin.lo)} to ${formatSignedMW(p.data.bin.hi)}`,
      },
      series: [
        {
          type: 'bar',
          barWidth: '92%',
          data: bins.map((b) => ({
            value: [b.lo + BIN_MW / 2, b.count],
            bin: b,
            itemStyle: {
              color: b.lo >= 0 ? colors.shortfall : colors.surplus,
              borderRadius: [3, 3, 0, 0],
            },
          })),
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: colors.ink, type: 'dashed', width: 1 },
            label: {
              ...baseText,
              color: colors.ink,
              formatter: (p: { name: string }) => p.name,
            },
            data: marks.map((m) => ({ name: m.name, xAxis: m.value })),
          },
        },
      ],
    }
  }, [points, summary])

  return (
    <ReactEChartsCore echarts={echarts} option={option} notMerge style={{ height: 280 }} />
  )
}

export const ErrorHistogram = memo(ErrorHistogramImpl)
