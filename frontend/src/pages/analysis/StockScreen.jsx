import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  InputNumber,
  Select,
  Space,
  Spin,
  Table,
  Typography,
  message,
} from 'antd';
import { DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';

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

function ratioOptionsFromApi(ratios) {
  return (ratios ?? []).map((field) => ({
    value: field.key,
    label: field.percent ? `${field.label} (%)` : field.label,
  }));
}

const OP_OPTIONS = [
  { value: 'gte', label: '≥' },
  { value: 'gt', label: '>' },
  { value: 'lte', label: '≤' },
  { value: 'lt', label: '<' },
  { value: 'eq', label: '=' },
];

let condKeySeq = 1;

function newRatioCondition() {
  return {
    key: `c-${condKeySeq++}`,
    field: 'ROE',
    op: 'gte',
    value: null,
  };
}

function matchesKeyword(row, keyword) {
  const q = keyword.trim().toLowerCase();
  if (!q) return true;
  return (
    String(row?.name ?? '')
      .toLowerCase()
      .includes(q) ||
    String(row?.ide ?? '')
      .toLowerCase()
      .includes(q)
  );
}

export default function StockScreen() {
  const [industries, setIndustries] = useState([]);
  const [industryOptions, setIndustryOptions] = useState([]);
  const [ratioOptions, setRatioOptions] = useState([]);
  const [ratioConds, setRatioConds] = useState([]);
  const [reportDate, setReportDate] = useState(undefined);
  const [reportDates, setReportDates] = useState([]);
  const [loadingMeta, setLoadingMeta] = useState(true);

  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  const [keyword, setKeyword] = useState('');
  const [stockFilters, setStockFilters] = useState(DEFAULT_STOCK_FILTERS);
  const [selectedStock, setSelectedStock] = useState(null);
  const [stockPage, setStockPage] = useState(1);
  const [stockPageSize, setStockPageSize] = useState(20);
  const [batchCategory, setBatchCategory] = useState(undefined);
  const [poolCategories, setPoolCategories] = useState([]);
  const [batchLoading, setBatchLoading] = useState(false);

  const { columns: baseColumns } = useStockTableColumns({
    onCriteriaChange: () => setStockPage(1),
  });

  const stockColumns = useMemo(() => {
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
        render: (v) => v || '—',
      },
      {
        title: '二级行业',
        dataIndex: 'hy2',
        key: 'hy2',
        width: 100,
        align: 'center',
        ellipsis: true,
        render: (v) => v || '—',
      },
      {
        title: '报告期',
        dataIndex: 'REPORTDATE',
        key: 'REPORTDATE',
        width: 110,
        align: 'center',
        render: (value) => (value ? String(value).slice(0, 10) : '—'),
      },
      ...base.slice(2),
    ];
  }, [baseColumns]);

  const filteredStocks = useMemo(
    () =>
      filterStocks(stocks, stockFilters).filter((row) => matchesKeyword(row, keyword)),
    [stocks, stockFilters, keyword],
  );

  useEffect(() => {
    let cancelled = false;
    setLoadingMeta(true);
    Promise.all([
      fetch('/api/hy/list/').then((res) => (res.ok ? res.json() : { sectors: [] })),
      fetch('/api/pool/categories/').then((res) => (res.ok ? res.json() : { categories: [] })),
      fetch('/api/update/ratios/').then((res) => (res.ok ? res.json() : { ratios: [] })),
      fetch('/api/screen/').then((res) => (res.ok ? res.json() : { report_dates: [] })),
    ])
      .then(([hyData, poolData, ratioData, screenData]) => {
        if (cancelled) return;
        setIndustryOptions(
          (hyData.sectors ?? []).map((s) => ({
            value: s.name,
            label: s.ide ? `${s.name}（${s.ide}）` : s.name,
          })),
        );
        setPoolCategories(poolData.categories ?? []);
        setRatioOptions(ratioOptionsFromApi(ratioData.ratios));
        setReportDates(screenData.report_dates ?? []);
      })
      .finally(() => {
        if (!cancelled) setLoadingMeta(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setStockPage(1);
  }, [stocks, keyword, stockFilters]);

  const updateCond = (key, patch) => {
    setRatioConds((prev) => prev.map((c) => (c.key === key ? { ...c, ...patch } : c)));
  };

  const handleSearch = useCallback(() => {
    const ratios = ratioConds
      .filter((c) => c.field && c.op && c.value != null && c.value !== '')
      .map(({ field, op, value }) => ({ field, op, value: Number(value) }));

    if (!industries.length && !ratios.length && !reportDate) {
      message.warning('请至少选择行业、报告期或设置一条比率条件');
      return;
    }

    setLoading(true);
    setError('');
    setSearched(true);
    setSelectedStock(null);

    fetch('/api/screen/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        industries,
        ratios,
        report_date: reportDate || null,
      }),
    })
      .then(async (res) => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(payload.error || '筛选失败');
        return payload;
      })
      .then((payload) => {
        setStocks(payload.stocks ?? []);
        message.success(`共筛选出 ${payload.count ?? 0} 只股票`);
      })
      .catch((err) => {
        setStocks([]);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [industries, ratioConds, reportDate]);

  const handleBatchAdd = async () => {
    const category = (batchCategory || '').trim();
    if (!category) {
      message.warning('请选择要加入的后选股分类');
      return;
    }
    if (!filteredStocks.length) {
      message.warning('当前没有可加入的股票');
      return;
    }
    setBatchLoading(true);
    let ok = 0;
    let fail = 0;
    try {
      // Ensure category exists.
      await fetch('/api/pool/categories/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category }),
      });
      for (const row of filteredStocks) {
        try {
          const res = await fetch(`/api/pool/stock/${encodeURIComponent(row.ide)}/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category }),
          });
          if (res.ok) ok += 1;
          else fail += 1;
        } catch {
          fail += 1;
        }
      }
      message.success(`已将 ${ok} 只加入「${category}」${fail ? `，失败 ${fail}` : ''}`);
      if (!poolCategories.includes(category)) {
        setPoolCategories((prev) => [...prev, category].sort());
      }
    } finally {
      setBatchLoading(false);
    }
  };

  const stockPagination = useMemo(
    () => ({
      current: stockPage,
      pageSize: stockPageSize,
      total: filteredStocks.length,
      size: 'small',
      showSizeChanger: true,
      pageSizeOptions: ['10', '20', '50', '100', '200', '500'],
      showTotal: (total) => `共 ${total} 条`,
      onChange: (page, pageSize) => {
        setStockPage(page);
        setStockPageSize(pageSize);
      },
    }),
    [stockPage, stockPageSize, filteredStocks.length],
  );

  return (
    <div className="industry-page">
      <div className="industry-page__header">
        <Title level={3} style={{ margin: 0 }}>
          股票筛选
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          按行业、报告期、财务比率筛选，并加入后选股
        </Text>
      </div>

      <Card title="筛选条件" size="small" loading={loadingMeta}>
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ display: 'block', marginBottom: 6 }}>
            行业
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

        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ display: 'block', marginBottom: 6 }}>
            报告期
          </Text>
          <Select
            allowClear
            showSearch
            placeholder="最新报告期"
            style={{ width: 220 }}
            value={reportDate}
            options={reportDates.map((date) => ({ value: date, label: date }))}
            onChange={setReportDate}
          />
          <Text type="secondary" style={{ display: 'block', marginTop: 4, fontSize: 12 }}>
            不选则按每只股票的最新报告期筛选
          </Text>
        </div>

        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ display: 'block', marginBottom: 6 }}>
            比率条件
          </Text>
          <Space direction="vertical" style={{ width: '100%' }} size={8}>
            {ratioConds.length === 0 ? (
              <Text type="secondary" style={{ fontSize: 12 }}>
                未设置比率条件（可只按行业或报告期筛选）
              </Text>
            ) : null}
            {ratioConds.map((cond) => (
              <Space key={cond.key} wrap>
                <Select
                  style={{ width: 240 }}
                  options={ratioOptions}
                  value={cond.field}
                  onChange={(field) => updateCond(cond.key, { field })}
                />
                <Select
                  style={{ width: 80 }}
                  options={OP_OPTIONS}
                  value={cond.op}
                  onChange={(op) => updateCond(cond.key, { op })}
                />
                <InputNumber
                  style={{ width: 120 }}
                  value={cond.value}
                  onChange={(value) => updateCond(cond.key, { value })}
                />
                <Button
                  icon={<DeleteOutlined />}
                  onClick={() => setRatioConds((prev) => prev.filter((c) => c.key !== cond.key))}
                />
              </Space>
            ))}
            <Button
              type="dashed"
              icon={<PlusOutlined />}
              onClick={() => setRatioConds((prev) => [...prev, newRatioCondition()])}
            >
              添加比率条件
            </Button>
          </Space>
        </div>

        <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleSearch}>
          开始筛选
        </Button>
      </Card>

      <section className="bankuai-section bankuai-section--stocks industry-body">
        <Card
          title={`筛选结果${searched ? `（${filteredStocks.length}）` : ''}`}
          size="small"
          className="bankuai-panel bankuai-panel--list bankuai-panel--stocks"
          extra={
            <Space wrap size="small">
              <Select
                size="small"
                allowClear
                placeholder="批量加入分类"
                style={{ minWidth: 140 }}
                value={batchCategory}
                options={poolCategories.map((name) => ({ value: name, label: name }))}
                onChange={setBatchCategory}
                dropdownRender={(menu) => (
                  <>
                    {menu}
                    <div style={{ padding: 8 }}>
                      <Input
                        size="small"
                        placeholder="输入新分类后回车"
                        onPressEnter={(e) => {
                          const name = e.currentTarget.value.trim();
                          if (!name) return;
                          setPoolCategories((prev) =>
                            prev.includes(name) ? prev : [...prev, name].sort(),
                          );
                          setBatchCategory(name);
                          e.currentTarget.value = '';
                        }}
                      />
                    </div>
                  </>
                )}
              />
              <Button size="small" loading={batchLoading} onClick={handleBatchAdd}>
                批量加入后选股
              </Button>
              <StockFilterDropdown
                filters={stockFilters}
                onChange={(key, checked) =>
                  setStockFilters((prev) => ({ ...prev, [key]: checked }))
                }
                onToggleAll={(checked) =>
                  setStockFilters(checked ? { ...ALL_STOCK_FILTERS } : { ...DEFAULT_STOCK_FILTERS })
                }
              />
            </Space>
          }
        >
          <Input.Search
            allowClear
            size="small"
            placeholder="搜索股票名称/代码"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 8 }} /> : null}
          {loading ? (
            <div className="bankuai-panel__center">
              <Spin />
            </div>
          ) : !searched ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="设置条件后点击「开始筛选」" />
          ) : (
            <Table
              className="bankuai-stock-table"
              rowKey={(row) => row.ide}
              columns={stockColumns}
              dataSource={filteredStocks}
              pagination={filteredStocks.length > 0 ? stockPagination : false}
              size="small"
              bordered
              scroll={{ x: 1300, y: 420 }}
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
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择筛选结果中的股票" />
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
