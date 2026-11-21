import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface SeriesItem {
  data: unknown[]
  type: string
  itemStyle?: { color: string }
}

interface DashboardChartProps {
  title: string
  type: 'bar' | 'pie' | 'line'
  data: unknown[]
}

export function DashboardChart({ title, type, data }: DashboardChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  let chart: echarts.ECharts | null = null

  useEffect(() => {
    if (!chartRef.current) return

    chart = echarts.init(chartRef.current)

    const options: echarts.EChartsOption = {
      title: { text: title, textStyle: { color: '#e2e8f0' } },
      tooltip: {},
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', axisLabel: { color: '#94a3b8' } },
      yAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
      series: [{ data, type, itemStyle: { color: '#10b981' } as SeriesItem }]
    }

    chart.setOption(options)

    return () => {
      if (chart) {
        chart.dispose()
      }
    }
  }, [title, type, data])

  return (
    <div ref={chartRef} style={{ height: '300px', width: '100%' }} />
  )
}

export default DashboardChart
