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
  Tooltip,
  Typography,
  message,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';

import EmbeddedFinanceTabs from '../../components/EmbeddedFinanceTabs';
import PoolCategoryControl from '../../components/PoolCategoryControl';
import StockChart from '../../components/StockChart';
import StockFilterDropdown, {
  ALL_STOCK_FILTERS,
  DEFAULT_STOCK_FILTERS,
} from '../../components/StockFilterDropdown';
import { useStockTableColumns } from '../../utils/sectorStockColumns';
import { filterStocks } from '../../utils/stockFilters';

const { Title, Text } = Typography;

const ALL_INDUSTRIES = '全部行业';

function matchesKeyword(row, keyword) {
  const q = keyword.trim().toLowerCase();
  if (!q) return true;
  return String(row?.name ?? '').toLowerCase().includes(q) || String(row?.ide ?? '').toLowerCase().includes(q);
}

function formatPct(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

function metricPercent(row, key) {
  const value = row?.metrics?.[key];
  return value == null ? '—' : `${value}%`;
}

export default function StockIndependentStrong() {
  const [industries, setIndustries] = useState([ALL_INDUSTRIES]);
  const [industryOptions, setIndustryOptions] = useState([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [mode, setMode] = useState('in');
  const [lookback, setLookback] = useState(80);
  const [pivotWindow, setPivotWindow] = useState(5);
  const [minScore, setMinScore] = useState(6);
  const [corrWindow, setCorrWindow] = useState(60);
  const [excessWindow, setExcessWindow] = useState(21);
  const [maxCorr, setMaxCorr] = useState(0.4);
  const [minExcess, setMinExcess] = useState(0);
  const [limit, setLimit] = useState(500);
  const [benchmark, setBenchmark] = useState('sh000001');

  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');
  const [keyword, setKeyword] = useState('');
  const [selectedStock, setSelectedStock] = useState(null);
  const [stockFilters, setStockFilters] = useState(DEFAULT_STOCK_FILTERS);

  useEffect(() => {
    let cancelled = false;
    setLoadingMeta(true);
    fetch('/api/hy/?level=1')
      .then((res) => (res.ok ? res.json() : { sectors: [] }))
      .then((payload) => {
        if (cancelled) return;
        const level1 = (payload.sectors ?? []).map((sector) => ({
          value: sector.name,
          label: sector.ide ? `${sector.name}（${sector.ide}）` : sector.name,
        }));
        setIndustryOptions([{ value: ALL_INDUSTRIES, label: '全部行业' }, ...level1]);
      })
      .finally(() => {
        if (!cancelled) setLoadingMeta(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleIndustriesChange = (values) => {
    const next = values || [];
    if (next.includes(ALL_INDUSTRIES) && !industries.includes(ALL_INDUSTRIES)) {
      setIndustries([ALL_INDUSTRIES]);
      return;
    }
    if (next.includes(ALL_INDUSTRIES) && next.length > 1) {
      setIndustries(next.filter((name) => name !== ALL_INDUSTRIES));
      return;
    }
    setIndustries(next);
  };

  const filteredStocks = useMemo(
    () => filterStocks(stocks, stockFilters).filter((row) => matchesKeyword(row, keyword)),
    [stocks, stockFilters, keyword],
  );

  const { columns: baseColumns, rangeSortColumn } = useStockTableColumns();

  const columns = useMemo(() => {
    const base = baseColumns;
    return [
      ...base.slice(0, 2),
      {
        title: '一级行业',
        dataIndex: 'hy1',
        key: 'hy1',
        width: 100,
        align: 'center',
        ellipsis: true,
        render: (value) => value || '—',
      },
      rangeSortColumn({
        title: '评分',
        dataIndex: 'score_text',
        key: 'score_text',
        width: 74,
        align: 'center',
        getValue: (row) => row.score,
        render: (value, row) => {
          const conditions = Object.entries(row.conditions ?? {});
          return (
            <Tooltip
              title={
                <div>
                  {conditions.map(([name, passed]) => (
                    <div key={name}>
                      {passed ? '通过' : '未通过'}：{name}
                    </div>
                  ))}
                </div>
              }
            >
              <span>{value || '—'}</span>
            </Tooltip>
          );
        },
      }),
      rangeSortColumn({
        title: '超额收益',
        dataIndex: 'excess',
        key: 'excess',
        width: 96,
        render: (value) => formatPct(value),
      }),
      rangeSortColumn({
        title: '相关度',
        dataIndex: 'corr',
        key: 'corr',
        width: 84,
        render: (value) => (value == null ? '—' : Number(value).toFixed(3)),
      }),
      rangeSortColumn({
        title: 'Beta',
        dataIndex: 'beta',
        key: 'beta',
        width: 72,
        render: (value) => (value == null ? '—' : Number(value).toFixed(2)),
      }),
      rangeSortColumn({
        title: '下轨斜率',
        key: 'lowSlope',
        width: 90,
        getValue: (row) => row.metrics?.下轨每日斜率百分比,
        render: (_, row) => metricPercent(row, '下轨每日斜率百分比'),
      }),
      {
        title: '日期',
        dataIndex: 'as_of',
        key: 'as_of',
        width: 96,
        align: 'center',
        render: (value) => value || '—',
      },
      ...base.slice(2),
    ];
  }, [baseColumns, rangeSortColumn]);

  const handleScan = () => {
    setLoading(true);
    setSearched(true);
    setError('');
    setSelectedStock(null);

    const scanAll = industries.includes(ALL_INDUSTRIES);
    fetch('/api/tech/independent-strong/scan/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode,
        industries: scanAll ? [ALL_INDUSTRIES] : industries,
        lookback,
        pivot_window: pivotWindow,
        min_score: minScore,
        corr_window: corrWindow,
        excess_window: excessWindow,
        max_corr: maxCorr,
        min_excess: minExcess,
        benchmark,
        limit,
      }),
    })
      .then(async (res) => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(payload.error || '独立走强扫描失败');
        return payload;
      })
      .then((payload) => {
        setStocks(payload.stocks ?? []);
        message.success(`找到 ${payload.count ?? 0} 只股票`);
      })
      .catch((err) => {
        setStocks([]);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="industry-page">
      <div className="industry-page__header">
        <Title level={3} style={{ margin: 0 }}>
          独立走强
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          上升通道 + 相对上证超额收益为正 + 与上证低相关
        </Text>
      </div>

      <Card title="扫描条件" size="small" loading={loadingMeta}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <div>
            <Text strong style={{ display: 'block', marginBottom: 6 }}>
              一级行业（可选「全部行业」）
            </Text>
            <Select
              mode="multiple"
              allowClear
              showSearch
              placeholder="选择一级行业，或全部行业"
              style={{ width: '100%' }}
              options={industryOptions}
              value={industries}
              onChange={handleIndustriesChange}
              optionFilterProp="label"
              maxTagCount="responsive"
            />
          </div>

          <Space wrap>
            <Radio.Group
              value={mode}
              onChange={(event) => setMode(event.target.value)}
              optionType="button"
              buttonStyle="solid"
              options={[
                { label: '当前处于通道', value: 'in' },
                { label: '刚进入通道', value: 'entered' },
              ]}
            />
            <Text>基准</Text>
            <Input
              value={benchmark}
              onChange={(event) => setBenchmark(event.target.value)}
              style={{ width: 120 }}
            />
            <Text>回看</Text>
            <InputNumber min={60} max={500} value={lookback} onChange={(value) => setLookback(value ?? 80)} />
            <Text>枢轴窗口</Text>
            <InputNumber
              min={3}
              max={31}
              value={pivotWindow}
              onChange={(value) => setPivotWindow(value ?? 5)}
            />
            <Text>最低评分</Text>
            <InputNumber min={1} max={7} value={minScore} onChange={(value) => setMinScore(value ?? 6)} />
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
              onChange={(value) => setMaxCorr(value ?? 0.4)}
            />
            <Text>超额 &gt;</Text>
            <InputNumber
              min={-1}
              max={2}
              step={0.01}
              value={minExcess}
              onChange={(value) => setMinExcess(value ?? 0)}
            />
            <Text>最多返回</Text>
            <InputNumber min={1} max={2000} value={limit} onChange={(value) => setLimit(value ?? 500)} />
            <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleScan}>
              开始扫描
            </Button>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            默认过滤：超额收益 &gt; 0 且相关度 &lt; 0.4（相对基准 {benchmark}）
          </Text>
        </Space>
      </Card>

      <section className="bankuai-section bankuai-section--stocks industry-body">
        <Card
          title={`扫描结果${searched ? `（${filteredStocks.length}）` : ''}`}
          size="small"
          className="bankuai-panel bankuai-panel--list bankuai-panel--stocks"
          extra={
            <StockFilterDropdown
              filters={stockFilters}
              onChange={(key, checked) =>
                setStockFilters((prev) => ({ ...prev, [key]: checked }))
              }
              onToggleAll={(checked) =>
                setStockFilters(checked ? { ...ALL_STOCK_FILTERS } : { ...DEFAULT_STOCK_FILTERS })
              }
            />
          }
        >
          <Input.Search
            allowClear
            size="small"
            placeholder="搜索股票名称/代码"
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
              dataSource={filteredStocks}
              pagination={
                filteredStocks.length > 20
                  ? { pageSize: 20, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }
                  : false
              }
              size="small"
              bordered
              scroll={{ x: 1700, y: 420 }}
              rowClassName={(row) => (selectedStock?.ide === row.ide ? 'row-selected' : '')}
              onRow={(row) => ({
                onClick: () => setSelectedStock(row),
                style: { cursor: 'pointer' },
              })}
            />
          )}
        </Card>

        <Card
          title={selectedStock ? `${selectedStock.name}（${selectedStock.ide}）` : '股票详情'}
          size="small"
          className="bankuai-panel bankuai-panel--chart bankuai-panel--stock-detail"
        >
          {!selectedStock ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择扫描结果中的股票" />
          ) : (
            <>
              <PoolCategoryControl ide={selectedStock.ide} compact />
              <StockChart ide={selectedStock.ide} height={260} />
              <div className="bankuai-dashboard">
                <EmbeddedFinanceTabs ide={selectedStock.ide} />
              </div>
            </>
          )}
        </Card>
      </section>
    </div>
  );
}
