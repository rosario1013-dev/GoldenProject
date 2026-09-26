import { useEffect, useMemo, useRef } from 'react';
import * as echarts from 'echarts';

import { darkAxisStyle, darkEchartsBase, darkSplitLine, TEXT } from '../../utils/theme';
import {
  formatAddedProfit,
  formatContribution,
  formatProfit,
} from '../../utils/industryProfitFormat';

export default function AddedProfitBars({ rows, onSelect }) {
  const ref = useRef(null);
  const chartRef = useRef(null);

  const data = useMemo(() => {
    const sorted = [...(rows || [])]
      .filter((r) => r.added_profit != null && Number(r.added_profit) > 0)
      .sort((a, b) => Number(b.added_profit) - Number(a.added_profit))
      .slice(0, 10);
    return sorted.reverse();
  }, [rows]);

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

    chart.setOption(
      {
        ...darkEchartsBase(),
        grid: { left: 100, right: 88, top: 16, bottom: 24 },
        tooltip: {
          ...darkEchartsBase().tooltip,
          formatter(params) {
            const row = params.data?.row || {};
            return [
              `<strong>${row.industry}</strong>`,
              `新增利润：${formatAddedProfit(row.added_profit)}`,
              `贡献度：${formatContribution(row.profit_contribution)}`,
              `当前利润：${formatProfit(row.current_profit)}`,
            ].join('<br/>');
          },
        },
        xAxis: {
          type: 'value',
          ...darkAxisStyle(),
          splitLine: darkSplitLine(),
          axisLabel: {
            color: TEXT.muted,
            formatter: (v) => formatProfit(v),
          },
        },
        yAxis: {
          type: 'category',
          data: data.map((r) => r.industry),
          ...darkAxisStyle(),
          axisLabel: { color: TEXT.body, width: 88, overflow: 'truncate' },
        },
        series: [
          {
            type: 'bar',
            data: data.map((row) => ({
              value: row.added_profit,
              row,
            })),
            itemStyle: { color: '#34d399' },
            label: {
              show: true,
              position: 'right',
              color: TEXT.muted,
              formatter: (p) =>
                `${formatAddedProfit(p.data.row.added_profit)}  ${formatContribution(p.data.row.profit_contribution)}`,
            },
          },
        ],
      },
      true,
    );

    const handler = (params) => {
      if (params?.data?.row) onSelect?.(params.data.row);
    };
    chart.off('click');
    chart.on('click', handler);
    return () => chart.off('click', handler);
  }, [data, onSelect]);

  return <div className="ipg-chart ipg-chart--bars" ref={ref} />;
}
