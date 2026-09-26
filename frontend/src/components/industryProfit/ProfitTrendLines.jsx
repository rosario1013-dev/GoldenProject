import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';

import { darkAxisStyle, darkEchartsBase, darkSplitLine, TEXT } from '../../utils/theme';
import { formatGrowthPct, formatProfit } from '../../utils/industryProfitFormat';

const COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f472b6', '#a78bfa'];

export default function ProfitTrendLines({ rows }) {
  const ref = useRef(null);
  const chartRef = useRef(null);

  const seriesRows = useMemo(() => (rows || []).slice(0, 5), [rows]);

  const years = useMemo(() => {
    const set = new Set();
    for (const row of seriesRows) {
      for (const point of row.yearly_series || []) {
        if (point?.year != null) set.add(Number(point.year));
      }
    }
    return [...set].sort((a, b) => a - b);
  }, [seriesRows]);

  useEffect(() => {
    if (!ref.current) return undefined;
    const chart = echarts.init(ref.current);
    chartRef.current = chart;
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const series = seriesRows.map((row, idx) => {
      const byYear = new Map(
        (row.yearly_series || []).map((p) => [Number(p.year), p.net_income]),
      );
      return {
        name: row.industry,
        type: 'line',
        smooth: true,
        showSymbol: true,
        data: years.map((y) => {
          const value = byYear.get(y);
          return value == null || Number.isNaN(Number(value)) ? null : Number(value);
        }),
        itemStyle: { color: COLORS[idx % COLORS.length] },
        lineStyle: { width: 2 },
      };
    });

    chart.setOption(
      {
        ...darkEchartsBase(),
        legend: {
          ...darkEchartsBase().legend,
          top: 0,
          type: 'scroll',
        },
        grid: { left: 64, right: 24, top: 40, bottom: 36 },
        tooltip: {
          ...darkEchartsBase().tooltip,
          trigger: 'axis',
          formatter(params) {
            const year = params?.[0]?.axisValue;
            const lines = [`<strong>${year}</strong>`];
            for (const p of params || []) {
              const row = seriesRows[p.seriesIndex];
              const seriesPoints = row?.yearly_series || [];
              const idx = seriesPoints.findIndex((x) => Number(x.year) === Number(year));
              const prev = idx > 0 ? seriesPoints[idx - 1]?.net_income : null;
              const curr = p.value;
              let yoy = null;
              if (curr != null && prev != null && Number(prev) > 0) {
                yoy = (Number(curr) / Number(prev) - 1) * 100;
              }
              lines.push(
                `${p.marker}${p.seriesName}：${formatProfit(curr)}（YoY ${formatGrowthPct(yoy)}）`,
              );
            }
            return lines.join('<br/>');
          },
        },
        xAxis: {
          type: 'category',
          data: years,
          ...darkAxisStyle(),
        },
        yAxis: {
          type: 'value',
          ...darkAxisStyle(),
          splitLine: darkSplitLine(),
          axisLabel: {
            color: TEXT.muted,
            formatter: (v) => formatProfit(v),
          },
        },
        series,
      },
      true,
    );
  }, [seriesRows, years]);

  return <div className="ipg-chart ipg-chart--trend" ref={ref} />;
}
