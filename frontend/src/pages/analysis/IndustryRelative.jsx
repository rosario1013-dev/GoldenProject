import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  InputNumber,
  Radio,
  Select,
  Space,
  Spin,
  Table,
  Typography,
  message,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';

import StockChart from '../../components/StockChart';
import { buildSectorChgColumns, IndustryLink } from '../../utils/sectorStockColumns';

const { Title, Text } = Typography;

function matchesKeyword(row, keyword) {
  const q = keyword.trim().toLowerCase();
  if (!q) return true;
  return (
    String(row?.name ?? '').toLowerCase().includes(q)
    || String(row?.ide ?? '').toLowerCase().includes(q)
    || String(row?.parent ?? '').toLowerCase().includes(q)
    || String(row?.code ?? '').toLowerCase().includes(q)
  );
}

function formatPct(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

export default function IndustryRelative() {
  const [parents, setParents] = useState([]);
  const [parentOptions, setParentOptions] = useState([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [level, setLevel] = useState('2');
  const [benchmark, setBenchmark] = useState('sh000001');
  const [corrWindow, setCorrWindow] = useState(60);
  const [excessWindow, setExcessWindow] = useState(21);
  const [maxCorr, setMaxCorr] = useState(null);
  const [minExcess, setMinExcess] = useState(null);
  const [limit, setLimit] = useState(500);

  const [sectors, setSectors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');
  const [keyword, setKeyword] = useState('');
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingMeta(true);
    fetch('/api/hy/?level=1')
      .then((res) => (res.ok ? res.json() : { sectors: [] }))
      .then((payload) => {
        if (cancelled) return;
        setParentOptions(
          (payload.sectors ?? []).map((sector) => ({
            value: sector.name,
            label: sector.ide ? `${sector.name}（${sector.ide}）` : sector.name,
          })),
        );
      })
      .finally(() => {
        if (!cancelled) setLoadingMeta(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(
    () => sectors.filter((row) => matchesKeyword(row, keyword)),
    [sectors, keyword],
  );

  const columns = useMemo(
    () => [
      {
        title: '代码',
        dataIndex: 'ide',
        key: 'ide',
        width: 96,
        align: 'center',
        fixed: 'left',
        render: (value) => value || '—',
      },
      {
        title: '行业',
        dataIndex: 'name',
        key: 'name',
        width: 120,
        align: 'center',
        fixed: 'left',
        ellipsis: true,
        render: (name) => <IndustryLink name={name}>{name || '—'}</IndustryLink>,
      },
      {
        title: '一级行业',
        dataIndex: 'parent',
        key: 'parent',
        width: 110,
        align: 'center',
        ellipsis: true,
        render: (name) => (name ? <IndustryLink name={name}>{name}</IndustryLink> : '—'),
      },
      {
        title: '相关度',
        dataIndex: 'corr',
        key: 'corr',
        width: 88,
        align: 'right',
        defaultSortOrder: 'ascend',
        sorter: (a, b) => (a.corr ?? Infinity) - (b.corr ?? Infinity),
        render: (value) => (value == null ? '—' : Number(value).toFixed(3)),
      },
      {
        title: 'Beta',
        dataIndex: 'beta',
        key: 'beta',
        width: 72,
        align: 'right',
        sorter: (a, b) => (a.beta ?? Infinity) - (b.beta ?? Infinity),
        render: (value) => (value == null ? '—' : Number(value).toFixed(2)),
      },
      {
        title: '超额收益',
        dataIndex: 'excess',
        key: 'excess',
        width: 96,
        align: 'right',
        sorter: (a, b) => (a.excess ?? -Infinity) - (b.excess ?? -Infinity),
        render: (value) => formatPct(value),
      },
      {
        title: '样本日',
        dataIndex: 'sample_days',
        key: 'sample_days',
        width: 72,
        align: 'center',
        sorter: (a, b) => (a.sample_days ?? 0) - (b.sample_days ?? 0),
      },
      {
        title: '日期',
        dataIndex: 'as_of',
        key: 'as_of',
        width: 96,
        align: 'center',
        render: (value) => value || '—',
      },
      ...buildSectorChgColumns(),
    ],
    [],
  );

  const handleScan = () => {
    setLoading(true);
    setSearched(true);
    setError('');
    setSelected(null);

    const body = {
      level,
      parents,
      benchmark,
      corr_window: corrWindow,
      excess_window: excessWindow,
      limit,
    };
    if (maxCorr != null) body.max_corr = maxCorr;
    if (minExcess != null) body.min_excess = minExcess;

    fetch('/api/tech/industry-relative/scan/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(async (res) => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(payload.error || `行业相关度扫描失败（HTTP ${res.status}）`);
        }
        return payload;
      })
      .then((payload) => {
        setSectors(payload.sectors ?? []);
        message.success(`找到 ${payload.count ?? 0} 个行业`);
      })
      .catch((err) => {
        setSectors([]);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="industry-page">
      <div className="industry-page__header">
        <Title level={3} style={{ margin: 0 }}>
          行业相关度
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          二级行业指数相对上证指数的相关度 / Beta / 超额收益
        </Text>
      </div>

      <Card title="扫描条件" size="small" loading={loadingMeta}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <div>
            <Text strong style={{ display: 'block', marginBottom: 6 }}>
              一级行业（不选则扫描全部二级行业）
            </Text>
            <Select
              mode="multiple"
              allowClear
              showSearch
              placeholder="选择一级行业以限定其下属二级行业"
              style={{ width: '100%' }}
              options={parentOptions}
              value={parents}
              onChange={setParents}
              optionFilterProp="label"
              maxTagCount="responsive"
              disabled={level !== '2'}
            />
          </div>

          <Space wrap>
            <Radio.Group
              value={level}
              onChange={(event) => {
                setLevel(event.target.value);
                if (event.target.value !== '2') setParents([]);
              }}
              optionType="button"
              buttonStyle="solid"
              options={[
                { label: '一级', value: '1' },
                { label: '二级', value: '2' },
                { label: '三级', value: '3' },
              ]}
            />
            <Text>基准</Text>
            <Input
              value={benchmark}
              onChange={(event) => setBenchmark(event.target.value)}
              style={{ width: 120 }}
            />
            <Text>相关窗口</Text>
            <InputNumber
              min={20}
              max={250}
              value={corrWindow}
              onChange={(value) => setCorrWindow(value ?? 60)}
            />
            <Text>超额窗口</Text>
            <InputNumber
              min={5}
              max={120}
              value={excessWindow}
              onChange={(value) => setExcessWindow(value ?? 21)}
            />
            <Text>相关度 &lt;</Text>
            <InputNumber
              min={0}
              max={1}
              step={0.05}
              value={maxCorr}
              placeholder="不限"
              onChange={setMaxCorr}
            />
            <Text>超额 &gt;</Text>
            <InputNumber
              min={-1}
              max={2}
              step={0.01}
              value={minExcess}
              placeholder="不限"
              onChange={setMinExcess}
            />
            <Text>最多返回</Text>
            <InputNumber min={1} max={2000} value={limit} onChange={(value) => setLimit(value ?? 500)} />
            <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleScan}>
              开始扫描
            </Button>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            默认不做过滤，按相关度升序排列；可选手动设置相关度上限或超额下限
          </Text>
        </Space>
      </Card>

      <section className="bankuai-section bankuai-section--stocks industry-body">
        <Card
          title={`扫描结果${searched ? `（${filtered.length}）` : ''}`}
          size="small"
          className="bankuai-panel bankuai-panel--list bankuai-panel--stocks"
        >
          <Input.Search
            allowClear
            size="small"
            placeholder="搜索行业名称/代码/一级行业"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            style={{ marginBottom: 8 }}
          />
          {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 8 }} /> : null}
          {loading ? (
            <div className="bankuai-panel__center">
              <Spin />
            </div>
          ) : !searched ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="设置条件后点击「开始扫描」" />
          ) : (
            <Table
              className="bankuai-stock-table"
              rowKey="ide"
              columns={columns}
              dataSource={filtered}
              pagination={
                filtered.length > 20
                  ? { pageSize: 20, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }
                  : false
              }
              size="small"
              bordered
              scroll={{ x: 1400, y: 420 }}
              rowClassName={(row) => (selected?.ide === row.ide ? 'row-selected' : '')}
              onRow={(row) => ({
                onClick: () => setSelected(row),
                style: { cursor: 'pointer' },
              })}
            />
          )}
        </Card>

        <Card
          title={selected ? `${selected.name}（${selected.ide}）` : '行业详情'}
          size="small"
          className="bankuai-panel bankuai-panel--chart bankuai-panel--stock-detail"
          extra={
            selected?.name ? (
              <Link to={`/industry/${encodeURIComponent(selected.name)}`} target="_blank" rel="noopener noreferrer">
                打开行业页
              </Link>
            ) : null
          }
        >
          {!selected ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择扫描结果中的行业" />
          ) : (
            <>
              <Space wrap style={{ marginBottom: 8 }}>
                <Text type="secondary">相关度 {selected.corr?.toFixed?.(3) ?? '—'}</Text>
                <Text type="secondary">Beta {selected.beta?.toFixed?.(2) ?? '—'}</Text>
                <Text type="secondary">超额 {formatPct(selected.excess)}</Text>
                <Text type="secondary">相对 {selected.benchmark || benchmark}</Text>
              </Space>
              <StockChart ide={selected.ide} height={320} />
            </>
          )}
        </Card>
      </section>
    </div>
  );
}
