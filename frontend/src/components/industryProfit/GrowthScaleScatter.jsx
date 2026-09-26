import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';

import { darkAxisStyle, darkEchartsBase, darkSplitLine, TEXT } from '../../utils/theme';
import {
  formatContribution,
  formatGrowthPct,
  formatProfit,
  growthMetricValue,
  periodLabel,
} from '../../utils/industryProfitFormat';

function median(values) {
  const nums = values.filter((v) => v != null && !Number.isNaN(Number(v))).map(Number).sort((a, b) => a - b);
  if (!nums.length) return null;
  const mid = Math.floor(nums.length / 2);
  return nums.length % 2 ? nums[mid] : (nums[mid - 1] + nums[mid]) / 2;
}

export default function GrowthScaleScatter({ rows, period, onSelect }) {
  const ref = useRef(null);
  const chartRef = useRef(null);

  const points = useMemo(
    () =>
      (rows || [])
        .map((row) => {
          const x = growthMetricValue(row, period);
          const y = row.current_profit;
          if (x == null || y == null || Number.isNaN(Number(x)) || Number.isNaN(Number(y))) {
            return null;
          }
          return {
            value: [Number(x), Number(y)],
            industry: row.industry,
            row,
          };
        })
        .filter(Boolean),
    [rows, period],
  );

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
    if (!chart) return undefined;

    const xs = points.map((p) => p.value[0]);
    const ys = points.map((p) => p.value[1]);
    const medX = median(xs);
    const medY = median(ys);

    const option = {
      ...darkEchartsBase(),
      grid: { left: 64, right: 24, top: 36, bottom: 48 },
      tooltip: {
        ...darkEchartsBase().tooltip,
        formatter(params) {
          const data = params.data;
          const row = data.row || {};
          return [
            `<strong>${data.industry}</strong>`,
            `利润：${formatProfit(row.current_profit)}`,
            `${periodLabel(period)}：${formatGrowthPct(growthMetricValue(row, period))}`,
            `3Y CAGR：${formatGrowthPct(row.profit_cagr_3y)}`,
            `贡献：${formatContribution(row.profit_contribution)}`,
          ].join('<br/>');
        },
      },
      xAxis: {
        name: `${periodLabel(period)} (%)`,
        nameLocation: 'middle',
        nameGap: 28,
        ...darkAxisStyle(),
        splitLine: darkSplitLine(),
        axisLine: { lineStyle: { color: '#334155' } },
      },
      yAxis: {
        name: '行业净利润',
        nameLocation: 'middle',
        nameGap: 48,
        ...darkAxisStyle(),
        splitLine: darkSplitLine(),
        axisLabel: {
          color: TEXT.muted,
          formatter: (v) => formatProfit(v),
        },
      },
      series: [
        {
          type: 'scatter',
          symbolSize: 12,
          data: points.map((p) => ({
            value: p.value,
            industry: p.industry,
            row: p.row,
          })),
          itemStyle: { color: '#60a5fa' },
          markLine:
            medX != null && medY != null
              ? {
                  symbol: 'none',
                  label: { color: TEXT.muted, formatter: '{b}' },
                  lineStyle: { type: 'dashed', color: '#64748b' },
                  data: [
                    { xAxis: medX, name: '增长中位' },
                    { yAxis: medY, name: '利润中位' },
                  ],
                }
              : undefined,
        },
      ],
      graphic: [
        {
          type: 'text',
          left: '68%',
          top: '18%',
          style: { text: '高增长 / 高利润', fill: '#86efac', fontSize: 12 },
        },
        {
          type: 'text',
          left: '68%',
          top: '72%',
          style: { text: '高增长 / 小规模', fill: '#93c5fd', fontSize: 12 },
        },
        {
          type: 'text',
          left: '12%',
          top: '18%',
          style: { text: '成熟高利润', fill: '#fcd34d', fontSize: 12 },
        },
        {
          type: 'text',
          left: '12%',
          top: '72%',
          style: { text: '低增长 / 小规模', fill: '#94a3b8', fontSize: 12 },
        },
      ],
    };

    chart.setOption(option, true);
    const handler = (params) => {
      if (params?.data?.row) onSelect?.(params.data.row);
    };
    chart.off('click');
    chart.on('click', handler);
    return () => chart.off('click', handler);
  }, [points, period, onSelect]);

  return <div className="ipg-chart ipg-chart--scatter" ref={ref} />;
}
