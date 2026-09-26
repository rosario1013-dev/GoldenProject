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

function matchesKeyword(row, keyword) {
  const q = keyword.trim().toLowerCase();
  if (!q) return true;
  return String(row?.name ?? '').toLowerCase().includes(q) || String(row?.ide ?? '').toLowerCase().includes(q);
}

function metricPercent(row, key) {
  const value = row?.metrics?.[key];
  return value == null ? '—' : `${value}%`;
}

export default function StockChannel() {
  const [industries, setIndustries] = useState([]);
  const [industryOptions, setIndustryOptions] = useState([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [mode, setMode] = useState('entered');
  const [lookback, setLookback] = useState(80);
  const [pivotWindow, setPivotWindow] = useState(5);
  const [minScore, setMinScore] = useState(6);
  const [limit, setLimit] = useState(500);

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
    fetch('/api/hy/list/')
      .then((res) => (res.ok ? res.json() : { sectors: [] }))
      .then((payload) => {
        if (cancelled) return;
        setIndustryOptions(
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
        title: '下轨斜率',
        key: 'lowSlope',
        width: 90,
        getValue: (row) => row.metrics?.下轨每日斜率百分比,
        render: (_, row) => metricPercent(row, '下轨每日斜率百分比'),
      }),
      rangeSortColumn({
        title: '上轨斜率',
        key: 'highSlope',
        width: 90,
        getValue: (row) => row.metrics?.上轨每日斜率百分比,
        render: (_, row) => metricPercent(row, '上轨每日斜率百分比'),
      }),
      rangeSortColumn({
        title: '通道宽度',
        key: 'width',
        width: 92,
        getValue: (row) => row.metrics?.通道平均宽度百分比,
        render: (_, row) => metricPercent(row, '通道平均宽度百分比'),
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

    fetch('/api/tech/channel/scan/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode,
        industries,
        lookback,
        pivot_window: pivotWindow,
        min_score: minScore,
        limit,
      }),
    })
      .then(async (res) => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(payload.error || '上升通道扫描失败');
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
          上升通道
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          从数据库行情中识别刚进入或当前处于上升通道的股票
        </Text>
      </div>

      <Card title="扫描条件" size="small" loading={loadingMeta}>
        <Space direction="vertical" style={{ width: '100%' }} size={12}>
          <div>
            <Text strong style={{ display: 'block', marginBottom: 6 }}>
              行业（不选则扫描全部股票）
            </Text>
            <Select
              mode="multiple"
              allowClear
              showSearch
              placeholder="选择一个或多个行业"
              style={{ width: '100%' }}
              options={industryOptions}
              value={industries}
              onChange={setIndustries}
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
                { label: '刚进入', value: 'entered' },
                { label: '当前处于', value: 'in' },
              ]}
            />
            <Text>回看交易日</Text>
            <InputNumber min={60} max={500} value={lookback} onChange={(value) => setLookback(value ?? 80)} />
            <Text>枢轴窗口</Text>
            <InputNumber min={3} max={31} value={pivotWindow} onChange={(value) => setPivotWindow(value ?? 5)} />
            <Text>最低评分</Text>
            <InputNumber min={1} max={7} value={minScore} onChange={(value) => setMinScore(value ?? 6)} />
            <Text>最多返回</Text>
            <InputNumber min={1} max={2000} value={limit} onChange={(value) => setLimit(value ?? 500)} />
            <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleScan}>
              开始扫描
            </Button>
          </Space>
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
              scroll={{ x: 1600, y: 420 }}
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
