import { useEffect, useMemo, useState } from 'react';
import { Alert, Card, Descriptions, Empty, Select, Space, Spin, Tag, Typography } from 'antd';

const { Text } = Typography;

const BENCHMARK_OPTIONS = [
  { label: '上证指数', value: 'sh000001' },
  { label: '沪深300', value: 'sh000300' },
  { label: '深证成指', value: 'sz399001' },
  { label: '创业板指', value: 'sz399006' },
];

function formatPct(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

function formatNum(value, digits = 3) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toFixed(digits);
}

export default function StockIndependentStrongRelation({ ide, embedded = false }) {
  const [benchmark, setBenchmark] = useState('sh000001');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [strictMatched, setStrictMatched] = useState(false);

  const conditionsTags = useMemo(() => {
    if (!result?.conditions || typeof result.conditions !== 'object') return [];
    return Object.entries(result.conditions).map(([key, passed]) => ({
      key,
      passed: Boolean(passed),
    }));
  }, [result]);

  useEffect(() => {
    if (!ide) return undefined;

    let cancelled = false;
    setLoading(true);
    setError('');
    setResult(null);
    setStrictMatched(false);

    const run = async (params) => {
      const res = await fetch('/api/tech/independent-strong/scan/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(payload.error || '独立走强计算失败');
      return payload;
    };

    const runStrict = async () => {
      return run({
        mode: 'in',
        industries: [],
        ides: [ide],
        benchmark,
        lookback: 80,
        pivot_window: 5,
        min_score: 6,
        corr_window: 60,
        excess_window: 21,
        max_corr: 0.4,
        min_excess: 0,
        limit: 1,
      });
    };

    const runRelaxed = async () => {
      // 放宽阈值：仍计算通道/相对指标，但尽量让结果返回，保证个股页可展示。
      return run({
        mode: 'in',
        industries: [],
        ides: [ide],
        benchmark,
        lookback: 80,
        pivot_window: 5,
        min_score: 0,
        corr_window: 60,
        excess_window: 21,
        max_corr: 1.0,
        min_excess: -1.0,
        limit: 1,
      });
    };

    (async () => {
      try {
        const strictPayload = await runStrict();
        const strictRow = (strictPayload?.stocks ?? [])[0] || null;
        if (cancelled) return;
        if (strictRow) {
          setStrictMatched(true);
          setResult(strictRow);
          return;
        }
        const relaxedPayload = await runRelaxed();
        const relaxedRow = (relaxedPayload?.stocks ?? [])[0] || null;
        if (cancelled) return;
        setStrictMatched(false);
        setResult(relaxedRow);
      } catch (e) {
        if (!cancelled) setError(e.message || '独立走强计算失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [ide, benchmark]);

  const body = (
    <>
      {strictMatched ? (
        <Alert
          type="success"
          showIcon
          message="满足独立走强（严格阈值）筛选条件"
          style={{ marginBottom: 12 }}
        />
      ) : result ? (
        <Alert
          type="info"
          showIcon
          message="未满足严格独立走强条件（已展示放宽阈值下的相对指标）"
          style={{ marginBottom: 12 }}
        />
      ) : null}

      <Space wrap style={{ marginBottom: 12 }}>
        <Text type="secondary">基准指数</Text>
        <Select
          size="small"
          style={{ width: 160 }}
          options={BENCHMARK_OPTIONS}
          value={benchmark}
          disabled={loading}
          onChange={(v) => setBenchmark(v)}
        />
      </Space>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 32 }}>
          <Spin />
        </div>
      ) : error ? (
        <Alert type="error" message={error} showIcon />
      ) : result ? (
        <>
          <Descriptions size="small" column={2} bordered>
            <Descriptions.Item label="通道评分">{result.score_text || '—'}</Descriptions.Item>
            <Descriptions.Item label="模式">{result.mode || '—'}</Descriptions.Item>
            <Descriptions.Item label="样本日期">{result.as_of || '—'}</Descriptions.Item>
            <Descriptions.Item label="指数">{result.benchmark || benchmark}</Descriptions.Item>
            <Descriptions.Item label="超额收益">{formatPct(result.excess, 2)}</Descriptions.Item>
            <Descriptions.Item label="相关度">{formatNum(result.corr, 3)}</Descriptions.Item>
            <Descriptions.Item label="Beta">{formatNum(result.beta, 2)}</Descriptions.Item>
          </Descriptions>

          {conditionsTags.length ? (
            <div style={{ marginTop: 12 }}>
              <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                通道条件（通过/未通过）
              </Text>
              <Space size={[4, 4]} wrap>
                {conditionsTags.map((t) => (
                  <Tag key={t.key} color={t.passed ? 'green' : 'red'} style={{ maxWidth: 240 }}>
                    {t.key}
                  </Tag>
                ))}
              </Space>
            </div>
          ) : null}
        </>
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可计算的独立走强结果" />
      )}
    </>
  );

  if (embedded) return body;

  return (
    <Card title="个股-指数独立走强关系" size="small" style={{ marginTop: 16 }}>
      {body}
    </Card>
  );
}

