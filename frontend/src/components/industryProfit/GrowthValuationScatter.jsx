import { useEffect, useMemo, useRef } from 'react';
import { Empty } from 'antd';
import * as echarts from 'echarts';

import { darkAxisStyle, darkEchartsBase, darkSplitLine, TEXT } from '../../utils/theme';
import { formatGrowthPct, formatScore } from '../../utils/industryProfitFormat';

export default function GrowthValuationScatter({ rows, onSelect }) {
  const ref = useRef(null);
  const chartRef = useRef(null);

  const points = useMemo(
    () =>
      (rows || [])
        .map((row) => {
          const x = row.valuation_score;
          const y = row.growth_score;
          if (x == null || y == null) return null;
          return { value: [Number(x), Number(y)], industry: row.industry, row };
        })
        .filter(Boolean),
    [rows],
  );

  useEffect(() => {
    if (!ref.current || !points.length) return undefined;
    const chart = echarts.init(ref.current);
    chartRef.current = chart;
    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      chart.dispose();
      chartRef.current = null;
    };
  }, [points.length]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !points.length) return undefined;

    chart.setOption(
      {
        ...darkEchartsBase(),
        grid: { left: 56, right: 24, top: 28, bottom: 40 },
        tooltip: {
          ...darkEchartsBase().tooltip,
          formatter(params) {
            const row = params.data.row || {};
            return [
              `<strong>${params.data.industry}</strong>`,
              `Growth Score：${formatScore(row.growth_score)}`,
              `Valuation：${formatScore(row.valuation_score)}`,
              `YoY：${formatGrowthPct(row.profit_growth_yoy)}`,
            ].join('<br/>');
          },
        },
        xAxis: {
          name: 'Industry Valuation Score',
          nameGap: 28,
          nameLocation: 'middle',
          min: 0,
          max: 100,
          ...darkAxisStyle(),
          splitLine: darkSplitLine(),
        },
        yAxis: {
          name: 'Profit Growth Score',
          nameGap: 40,
          nameLocation: 'middle',
          min: 0,
          max: 100,
          ...darkAxisStyle(),
          splitLine: darkSplitLine(),
        },
        series: [
          {
            type: 'scatter',
            data: points,
            symbolSize: 12,
            itemStyle: { color: '#f472b6' },
            markLine: {
              symbol: 'none',
              lineStyle: { type: 'dashed', color: '#64748b' },
              data: [{ xAxis: 50 }, { yAxis: 50 }],
            },
          },
        ],
        graphic: [
          {
            type: 'text',
            left: '18%',
            top: '18%',
            style: {
              text: 'High Growth + Low Valuation',
              fill: '#86efac',
              fontSize: 12,
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
  }, [points, onSelect]);

  if (!points.length) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="行业 Valuation Score 暂未就绪，预留 Growth × Valuation 分析入口"
      />
    );
  }

  return <div className="ipg-chart ipg-chart--scatter" ref={ref} />;
}
