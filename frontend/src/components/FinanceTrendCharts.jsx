import { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Card, Col, Empty, Row, Segmented, Space, Spin, Switch } from 'antd';
import * as echarts from 'echarts';

import {
  DEFAULT_VISIBLE_FROM_YEAR,
  PERIOD_MODES,
  calcYoYChange,
  filterColumnsByPeriod,
  formatColumnTitle,
  formatYoYChange,
  getColumnYear,
  resolveDisplayColumns,
} from '../utils/cwColumns';
import { formatFinance, formatFinanceRaw } from '../utils/formatFinance';
import { darkAxisStyle, darkEchartsBase, darkSplitLine, TEXT } from '../utils/theme';

const METRICS = [
  {
    key: 'revenue',
    title: '营业总收入',
    account: '营业总收入',
    barColor: '#5470c6',
    lineColor: '#91cc75',
  },
  {
    key: 'netProfit',
    title: '归属于母公司股东的净利润',
    account: '归属于母公司股东的净利润',
    barColor: '#ee6666',
    lineColor: '#73c0de',
  },
];

function normalizeReportDate(value) {
  if (value == null) return '';
  const text = String(value);
  const match = text.match(/(\d{4}-\d{2}-\d{2})/);
  return match ? match[1] : text.slice(0, 10);
}

function fetchAccountSeries(ide, account) {
  return fetch(`/api/stock/${encodeURIComponent(ide)}/ratio/${encodeURIComponent(account)}/`).then(
    async (res) => {
      if (!res.ok) {
        let message = `${account} 加载失败`;
        try {
          const payload = await res.json();
          if (payload?.error) message = payload.error;
        } catch {
          // ignore non-JSON error bodies
        }
        throw new Error(message);
      }
      return res.json();
    },
  );
}

function buildChartPoints(rawData, periodMode, showOlder) {
  const byDate = new Map();
  for (const item of rawData || []) {
    const date = normalizeReportDate(item.report_date);
    const value = item.value == null ? null : Number(item.value);
    if (!date || value == null || Number.isNaN(value)) continue;
    byDate.set(date, value);
  }

  const allDates = [...byDate.keys()].sort();
  const periodDates = filterColumnsByPeriod(allDates, periodMode);
  const visibleDates = resolveDisplayColumns(periodDates, {
    showOlder,
    cutoffYear: DEFAULT_VISIBLE_FROM_YEAR,
  }).sort();

  return visibleDates.map((date) => {
    const value = byDate.get(date);
    const priorDate = `${Number(date.slice(0, 4)) - 1}${date.slice(4)}`;
    const prior = byDate.has(priorDate) ? byDate.get(priorDate) : null;
    const yoy = calcYoYChange(value, prior, false);
    return { date, value, yoy };
  });
}

function axisUnit(values) {
  const maxAbs = Math.max(0, ...values.map((v) => (v == null ? 0 : Math.abs(Number(v)))));
  if (maxAbs >= 1e8) return { divisor: 1e8, label: '亿' };
  if (maxAbs >= 1e4) return { divisor: 1e4, label: '万' };
  return { divisor: 1, label: '元' };
}

function MetricChart({ title, points, periodMode, barColor, lineColor }) {
  const chartRef = useRef(null);
  const chartInstanceRef = useRef(null);

  const option = useMemo(() => {
    if (!points.length) return null;

    const categories = points.map((p) => formatColumnTitle(p.date, periodMode));
    const values = points.map((p) => p.value);
    const yoyValues = points.map((p) => p.yoy);
    const { divisor, label } = axisUnit(values);
    const scaled = values.map((v) => (v == null ? null : Number((v / divisor).toFixed(4))));

    const barColors = scaled.map((v) => {
      if (v == null) return barColor;
      if (v < 0) return '#3f8600';
      return barColor;
    });

    const axisStyle = darkAxisStyle();

    return {
      ...darkEchartsBase(),
      animationDuration: 300,
      grid: { left: 52, right: 52, top: 40, bottom: 48 },
      legend: {
        data: ['金额', '同比'],
        top: 4,
        textStyle: { fontSize: 12, color: TEXT.muted },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: '#111827',
        borderColor: '#334155',
        textStyle: { color: TEXT.body },
        formatter(params) {
          const idx = params?.[0]?.dataIndex ?? 0;
          const point = points[idx];
          if (!point) return '';
          const lines = [
            formatColumnTitle(point.date, periodMode),
            `金额：${formatFinance(point.value)}（${formatFinanceRaw(point.value) || '—'}）`,
          ];
          const yoyText = formatYoYChange(point.yoy, false);
          lines.push(`同比：${yoyText || '—'}`);
          return lines.join('<br/>');
        },
      },
      xAxis: {
        type: 'category',
        data: categories,
        ...axisStyle,
        axisLabel: {
          rotate: periodMode === PERIOD_MODES.QUARTER ? 45 : 0,
          fontSize: 11,
          hideOverlap: true,
          color: TEXT.muted,
        },
      },
      yAxis: [
        {
          type: 'value',
          name: label,
          scale: true,
          ...axisStyle,
          splitLine: darkSplitLine(),
          axisLabel: {
            color: TEXT.muted,
            formatter: (v) => {
              const num = Number(v);
              if (Math.abs(num) >= 100) return num.toFixed(0);
              return String(Number(num.toFixed(2)));
            },
          },
        },
        {
          type: 'value',
          name: '%',
          scale: true,
          ...axisStyle,
          splitLine: { show: false },
          axisLabel: {
            color: TEXT.muted,
            formatter: (v) => `${Number(v).toFixed(0)}%`,
          },
        },
      ],
      series: [
        {
          name: '金额',
          type: 'bar',
          data: scaled.map((v, i) => ({
            value: v,
            itemStyle: { color: barColors[i] },
          })),
          barMaxWidth: 28,
        },
        {
          name: '同比',
          type: 'line',
          yAxisIndex: 1,
          data: yoyValues,
          smooth: true,
          showSymbol: points.length <= 24,
          symbolSize: 6,
          itemStyle: { color: lineColor },
          lineStyle: { width: 2, color: lineColor },
        },
      ],
    };
  }, [points, periodMode, barColor, lineColor]);

  useEffect(() => {
    if (!chartRef.current || !option) return undefined;

    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current);
    }
    const chart = chartInstanceRef.current;
    chart.setOption(option, true);

    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
    };
  }, [option]);

  useEffect(
    () => () => {
      chartInstanceRef.current?.dispose();
      chartInstanceRef.current = null;
    },
    [],
  );

  if (!points.length) {
    return (
      <div>
        <div style={{ fontWeight: 500, marginBottom: 8 }}>{title}</div>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
      </div>
    );
  }

  return (
    <div>
      <div style={{ fontWeight: 500, marginBottom: 4 }}>{title}</div>
      <div ref={chartRef} style={{ width: '100%', height: 300 }} />
    </div>
  );
}

export default function FinanceTrendCharts({ ide, embedded = false }) {
  const [seriesMap, setSeriesMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [periodMode, setPeriodMode] = useState(PERIOD_MODES.QUARTER);
  const [showOlder, setShowOlder] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    setSeriesMap({});

    Promise.all(METRICS.map((metric) => fetchAccountSeries(ide, metric.account)))
      .then((payloads) => {
        if (cancelled) return;
        const next = {};
        payloads.forEach((payload, index) => {
          next[METRICS[index].key] = payload?.data ?? [];
        });
        setSeriesMap(next);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '财务趋势加载失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ide]);

  const chartData = useMemo(() => {
    const result = {};
    for (const metric of METRICS) {
      result[metric.key] = buildChartPoints(seriesMap[metric.key], periodMode, showOlder);
    }
    return result;
  }, [seriesMap, periodMode, showOlder]);

  const hasOlder = useMemo(() => {
    return METRICS.some((metric) => {
      const dates = (seriesMap[metric.key] || [])
        .map((item) => normalizeReportDate(item.report_date))
        .filter(Boolean);
      const periodDates = filterColumnsByPeriod(dates, periodMode);
      return periodDates.some((col) => {
        const year = getColumnYear(col);
        return year != null && year < DEFAULT_VISIBLE_FROM_YEAR;
      });
    });
  }, [seriesMap, periodMode]);

  const controls = (
    <Space size="middle" wrap>
      <Segmented
        size="small"
        value={periodMode}
        onChange={setPeriodMode}
        options={[
          { label: '季度', value: PERIOD_MODES.QUARTER },
          { label: '年度', value: PERIOD_MODES.YEAR },
        ]}
      />
      {hasOlder ? (
        <Space size={6}>
          <span style={{ fontSize: 12, color: TEXT.muted }}>更早年份</span>
          <Switch size="small" checked={showOlder} onChange={setShowOlder} />
        </Space>
      ) : null}
    </Space>
  );

  const body = (
    <>
      {embedded ? <div style={{ marginBottom: 12 }}>{controls}</div> : null}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin />
        </div>
      ) : null}
      {error ? <Alert type="error" message={error} showIcon /> : null}
      {!loading && !error ? (
        <Row gutter={[16, 16]}>
          {METRICS.map((metric) => (
            <Col key={metric.key} xs={24} lg={12}>
              <MetricChart
                title={metric.title}
                points={chartData[metric.key] || []}
                periodMode={periodMode}
                barColor={metric.barColor}
                lineColor={metric.lineColor}
              />
            </Col>
          ))}
        </Row>
      ) : null}
    </>
  );

  if (embedded) return body;

  return (
    <Card title="财务趋势" size="small" style={{ marginTop: 16 }} extra={controls}>
      {body}
    </Card>
  );
}
