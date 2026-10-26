import ReactEChartsCore from 'echarts-for-react/lib/core'
import { memo, useMemo } from 'react'
import type { SeriesPoint } from '../api/types'
import { colors } from '../lib/colors'
import { baseText, echarts, lineKey, tooltipBase, valueAxisMW } from '../lib/echarts'
import { formatHours, formatMW, formatSignedMW, formatUkAxis, formatUkDateTime } from '../lib/format'

interface MainChartProps {
  points: SeriesPoint[]
  /** When set, draws forecast minus this buffer: the P90 "wind floor" (in-sample). */
  floorBufferMw?: number | null
}

type TooltipParam = { axisValue: number }

/** Actual vs selected forecast (top) and signed error per hour (bottom), sharing one zoom. */
function MainChartImpl({ points, floorBufferMw }: MainChartProps) {
  const option = useMemo(() => {
    const byTime = new Map<number, SeriesPoint>()
    const actual: [number, number | null][] = []
    const forecast: [number, number | null][] = []
    const floor: [number, number | null][] = []
    const errors: { value: [number, number | null]; itemStyle: { color: string } }[] = []

    for (const p of points) {
      const t = Date.parse(p.start_time)
      byTime.set(t, p)
      actual.push([t, p.actual_mw])
      // Forecasts are hourly: :30 rows are null by design, not gaps, so leave them out.
      // A null on the hour is a real gap and stays a break in the line.
      if (new Date(t).getUTCMinutes() === 0) {
        forecast.push([t, p.forecast_mw])
        if (floorBufferMw != null)
          floor.push([t, p.forecast_mw == null ? null : p.forecast_mw - floorBufferMw])
        errors.push({
          value: [t, p.error_mw],
          itemStyle: { color: (p.error_mw ?? 0) > 0 ? colors.shortfall : colors.surplus },
        })
      }
    }

    const tooltipFormatter = (params: TooltipParam[] | TooltipParam) => {
      const first = Array.isArray(params) ? params[0] : params
      const t = Number(first?.axisValue)
      // Hovering a :30 slot: show the forecast context of its hour.
      const p = byTime.get(t)
      const hourPoint = byTime.get(t - (new Date(t).getUTCMinutes() === 30 ? 30 * 60_000 : 0))
      if (!p) return ''
      const fc = hourPoint?.forecast_mw ?? null
      const rows = [
        `<div style="font-weight:600;margin-bottom:4px">${formatUkDateTime(t)} <span style="color:${colors.muted};font-weight:400">UK</span></div>`,
        `${lineKey(colors.actual)}<b>${formatMW(p.actual_mw)}</b> <span style="color:${colors.inkSecondary}">actual</span>`,
        `${lineKey(colors.forecast)}<b>${formatMW(fc)}</b> <span style="color:${colors.inkSecondary}">forecast${p === hourPoint ? '' : ' (hourly)'}</span>`,
      ]
      if (p.error_mw != null) {
        const c = p.error_mw > 0 ? colors.shortfall : colors.inkSecondary
        rows.push(
          `<span style="color:${c}"><b>${formatSignedMW(p.error_mw)}</b> ${p.error_mw > 0 ? 'shortfall' : 'surplus'}</span>`,
        )
      }
      if (hourPoint?.publish_time) {
        rows.push(
          `<div style="margin-top:4px;color:${colors.muted}">Published ${formatUkDateTime(hourPoint.publish_time)} UK, lead ${formatHours(hourPoint.lead_time_hours)}</div>`,
        )
      }
      return rows.join('<br/>')
    }

    const timeAxis = (gridIndex: number, showLabels: boolean) => ({
      type: 'time' as const,
      gridIndex,
      axisLabel: {
        ...baseText,
        color: colors.muted,
        show: showLabels,
        hideOverlap: true,
        formatter: (v: number) => formatUkAxis(v),
      },
      axisLine: { lineStyle: { color: colors.axis } },
      axisTick: { show: false },
      splitLine: { show: false },
    })

    return {
      animation: false,
      useUTC: true, // ticks at UTC midnights (UK midnight in GMT), not the viewer's local zone
      textStyle: baseText,
      legend: {
        top: 0,
        right: 0,
        itemWidth: 14,
        itemHeight: 2,
        textStyle: { ...baseText, color: colors.inkSecondary },
        data: [
          { name: 'Actual', icon: 'rect' },
          { name: 'Forecast at decision time', icon: 'rect' },
          ...(floorBufferMw != null ? [{ name: 'P90 wind floor (backtest)', icon: 'rect' }] : []),
        ],
      },
      grid: [
        { left: 56, right: 16, top: 32, height: '58%' },
        { left: 56, right: 16, top: '74%', bottom: 56 },
      ],
      xAxis: [timeAxis(0, false), timeAxis(1, true)],
      yAxis: [
        { ...valueAxisMW, gridIndex: 0 },
        {
          ...valueAxisMW,
          gridIndex: 1,
          name: 'Error MW',
          splitNumber: 2,
        },
      ],
      axisPointer: { link: [{ xAxisIndex: 'all' }], lineStyle: { color: colors.axis } },
      tooltip: { ...tooltipBase, trigger: 'axis', formatter: tooltipFormatter },
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1] },
        {
          type: 'slider',
          xAxisIndex: [0, 1],
          bottom: 8,
          height: 20,
          borderColor: colors.grid,
          labelFormatter: (v: number) => formatUkAxis(v),
          textStyle: { ...baseText, color: colors.muted },
        },
      ],
      series: [
        {
          name: 'Actual',
          type: 'line',
          data: actual,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 2, color: colors.actual },
          itemStyle: { color: colors.actual },
        },
        {
          name: 'Forecast at decision time',
          type: 'line',
          data: forecast,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 2, color: colors.forecast },
          itemStyle: { color: colors.forecast },
        },
        ...(floorBufferMw != null
          ? [
              {
                name: 'P90 wind floor (backtest)',
                type: 'line',
                data: floor,
                showSymbol: false,
                connectNulls: false,
                lineStyle: { width: 1.5, type: 'dashed', color: colors.floor },
                itemStyle: { color: colors.floor },
              },
            ]
          : []),
        {
          name: 'Error',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: errors,
          barMaxWidth: 6,
          markLine: {
            silent: true,
            symbol: 'none',
            label: { show: false },
            lineStyle: { color: colors.axis, type: 'solid', width: 1 },
            data: [{ yAxis: 0 }],
          },
        },
      ],
    }
  }, [points, floorBufferMw])

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      style={{ height: 420, width: '100%' }}
    />
  )
}

export const MainChart = memo(MainChartImpl)
