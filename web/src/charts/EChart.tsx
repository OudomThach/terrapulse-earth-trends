/** A resize-aware ECharts canvas. Callers should memoise ``option`` so the chart only redraws when data changes. */

import { BarChart, HeatmapChart, LineChart } from 'echarts/charts'
import {
  DataZoomComponent, GridComponent, LegendComponent, MarkLineComponent, MarkPointComponent, TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import * as echarts from 'echarts/core'
import type { EChartsCoreOption } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { useEffect, useRef } from 'react'

echarts.use([
  LineChart, BarChart, HeatmapChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent,
  MarkLineComponent, MarkPointComponent, VisualMapComponent, CanvasRenderer,
])

/** Thin wrapper that renders an ECharts option and resizes with its container. */
export function EChart({ option, height = 360, label }: { option: EChartsCoreOption; height?: number; label: string }) {
  const host = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    const el = host.current
    if (!el) return
    const instance = echarts.init(el, undefined, { renderer: 'canvas' })
    chart.current = instance
    const observer = new ResizeObserver(() => instance.resize())
    observer.observe(el)
    return () => {
      observer.disconnect()
      instance.dispose()
      chart.current = null
    }
  }, [])

  useEffect(() => {
    chart.current?.setOption(option, true)
  }, [option])

  return <div ref={host} className="chart" style={{ height }} role="img" aria-label={label} />
}
