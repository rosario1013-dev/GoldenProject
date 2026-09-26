import { useEffect, useMemo, useState } from 'react';
import { Alert, Card, Input, Spin, Table, Typography } from 'antd';

import { formatPct, getRateClassName } from '../../utils/rateStyle';

const { Title, Paragraph } = Typography;

function buildValueColumns(ratios) {
  const ratioColumns = (ratios ?? []).map((field) => ({
    title: field.label || field.key,
    dataIndex: field.key,
    key: field.key,
    width: 140,
    render: field.percent
      ? (value) => <span className={getRateClassName(value)}>{formatPct(value)}</span>
      : (value) => {
          if (value == null || Number.isNaN(Number(value))) return '—';
          return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 4 });
        },
  }));
  return [
    { title: '报告期', dataIndex: 'REPORTDATE', key: 'REPORTDATE', width: 120, fixed: 'left' },
    ...ratioColumns,
  ];
}

export default function RatioAnalysis() {
  const [ratioInfo, setRatioInfo] = useState(null);
  const [ide, setIde] = useState('sh600519');
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('/api/update/ratios/')
      .then((res) => res.json())
      .then((data) => setRatioInfo(data))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!ide.trim()) return undefined;

    let cancelled = false;
    setDataLoading(true);
    setError('');

    fetch(`/api/stock/${encodeURIComponent(ide.trim())}/fsa/`)
      .then((res) => {
        if (!res.ok) throw new Error('暂无比率数据，请先在资料更新中执行比率更新');
        return res.json();
      })
      .then((payload) => {
        if (!cancelled) setRows(payload.data ?? []);
      })
      .catch((err) => {
        if (!cancelled) {
          setRows([]);
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) setDataLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ide]);

  const valueColumns = useMemo(
    () => buildValueColumns(ratioInfo?.ratios),
    [ratioInfo],
  );

  const definitionColumns = useMemo(
    () => [
      { title: '字段', dataIndex: 'key', key: 'key', width: 140 },
      { title: '名称', dataIndex: 'label', key: 'label', width: 180 },
      { title: 'GP_FSA 账户', dataIndex: 'account', key: 'account', width: 180 },
      { title: '说明', dataIndex: 'description', key: 'description' },
    ],
    [],
  );

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={2}>比率分析</Title>
      <Paragraph type="secondary">
        展示 GP_FSA 计算的财务比率（存储于 tdx.FSA）。可在「资料更新 → 比率更新」中批量计算上传。
      </Paragraph>

      <Card title="比率字段定义" size="small" style={{ marginBottom: 16 }}>
        <Table
          size="small"
          rowKey="key"
          pagination={false}
          columns={definitionColumns}
          dataSource={ratioInfo?.ratios ?? []}
          scroll={{ x: 720 }}
        />
      </Card>

      <Card title="股票比率查询" size="small">
        <Input
          value={ide}
          onChange={(e) => setIde(e.target.value)}
          placeholder="输入股票代码，如 sh600519"
          style={{ width: 280, marginBottom: 12 }}
        />
        {error ? <Alert type="warning" showIcon message={error} style={{ marginBottom: 12 }} /> : null}
        <Table
          size="small"
          rowKey={(row) => `${row.IDE}-${row.REPORTDATE}`}
          loading={dataLoading}
          pagination={false}
          columns={valueColumns}
          dataSource={rows}
          scroll={{ x: 2200 }}
        />
      </Card>
    </div>
  );
}
