import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Card, Empty, Input, Space, Spin, Table, Tag, Tooltip, Typography } from 'antd';

import EmbeddedFinanceTabs from '../components/EmbeddedFinanceTabs';
import PoolCategoryControl, { PoolCategoryManager } from '../components/PoolCategoryControl';
import StockChart from '../components/StockChart';
import { useStockTableColumns } from '../utils/sectorStockColumns';

const { Title, Text } = Typography;

const SWING_BUY_COLOR = '#2e7d32';
const SWING_SELL_COLOR = '#c62828';
const RECENT_SWING_DAYS = 3;

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

function formatSwingDate(time) {
  const raw = String(time ?? '');
  return raw.length >= 10 ? raw.slice(5) : raw || '—';
}

function RecentSwingCell({ summary, loading }) {
  if (loading && !summary) {
    return <Spin size="small" />;
  }
  if (!summary || (!summary.buy && !summary.sell)) {
    return <Text type="secondary">—</Text>;
  }

  const tip = (summary.markers ?? [])
    .map((m) => `${m.kind === 'low' ? '买' : '卖'} ${m.time}`)
    .join(' · ');

  return (
    <Tooltip title={tip || undefined}>
      <Space size={4} wrap>
        {summary.buy ? (
          <Tag className="pool-swing-tag pool-swing-tag--buy" color={SWING_BUY_COLOR}>
            买
          </Tag>
        ) : null}
        {summary.sell ? (
          <Tag className="pool-swing-tag pool-swing-tag--sell" color={SWING_SELL_COLOR}>
            卖
          </Tag>
        ) : null}
        {(summary.markers ?? []).length === 1 ? (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {formatSwingDate(summary.markers[0].time)}
          </Text>
        ) : null}
      </Space>
    </Tooltip>
  );
}

function swingSortValue(summary) {
  if (!summary) return 0;
  return (summary.buy ? 2 : 0) + (summary.sell ? 1 : 0);
}

export default function Pool() {
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState('');
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [keyword, setKeyword] = useState('');
  const [selectedStock, setSelectedStock] = useState(null);
  const [stockPage, setStockPage] = useState(1);
  const [stockPageSize, setStockPageSize] = useState(20);
  const [recentSwings, setRecentSwings] = useState({});
  const [swingsLoading, setSwingsLoading] = useState(false);

  const { columns: baseColumns } = useStockTableColumns({
    onCriteriaChange: () => setStockPage(1),
  });

  const stockColumns = useMemo(() => {
    // buildStockTableColumns: [代码, 名称, ...FSA, ...涨幅]
    // Pool list is narrow and already has a 分类 column, so put 涨幅
    // immediately after 名称/分类 — otherwise they stay off-screen to the right.
    const base = baseColumns;
    const identity = base.slice(0, 2);
    const metrics = base.slice(2);
    const fsaCount = metrics.findIndex((col) => String(col.key || '').startsWith('chg_'));
    const fsaCols = fsaCount >= 0 ? metrics.slice(0, fsaCount) : metrics;
    const chgCols = fsaCount >= 0 ? metrics.slice(fsaCount) : [];
    return [
      ...identity,
      {
        title: '分类',
        dataIndex: 'categories',
        key: 'categories',
        width: 120,
        ellipsis: true,
        render: (cats) => (Array.isArray(cats) && cats.length ? cats.join('、') : '—'),
      },
      {
        title: `近${RECENT_SWING_DAYS}日`,
        key: 'recent_swing',
        width: 88,
        align: 'center',
        fixed: 'left',
        sorter: (a, b) =>
          swingSortValue(recentSwings[a.ide]) - swingSortValue(recentSwings[b.ide]),
        render: (_, row) => (
          <RecentSwingCell summary={recentSwings[row.ide]} loading={swingsLoading} />
        ),
      },
      ...chgCols,
      ...fsaCols,
    ];
  }, [baseColumns, recentSwings, swingsLoading]);

  const filteredStocks = useMemo(
    () => stocks.filter((row) => matchesKeyword(row, keyword)),
    [stocks, keyword],
  );

  const loadRecentSwings = useCallback((category) => {
    setSwingsLoading(true);
    const params = new URLSearchParams({ days: String(RECENT_SWING_DAYS) });
    if (category) params.set('category', category);
    return fetch(`/api/pool/recent-swings/?${params}`)
      .then((res) => {
        if (!res.ok) throw new Error('近三日买卖点加载失败');
        return res.json();
      })
      .then((payload) => {
        setRecentSwings(payload.swings ?? {});
      })
      .catch(() => {
        setRecentSwings({});
      })
      .finally(() => setSwingsLoading(false));
  }, []);

  const loadStocks = useCallback((category) => {
    setLoading(true);
    setError('');
    setSelectedStock(null);
    setRecentSwings({});
    const params = new URLSearchParams();
    if (category) params.set('category', category);
    return fetch(`/api/pool/stocks/?${params}`)
      .then((res) => {
        if (!res.ok) throw new Error('股票池加载失败');
        return res.json();
      })
      .then((payload) => {
        setStocks(payload.stocks ?? []);
        loadRecentSwings(category);
      })
      .catch((err) => {
        setError(err.message);
        setStocks([]);
        setRecentSwings({});
      })
      .finally(() => setLoading(false));
  }, [loadRecentSwings]);

  useEffect(() => {
    loadStocks(activeCategory);
  }, [activeCategory, loadStocks]);

  useEffect(() => {
    setStockPage(1);
  }, [activeCategory, keyword, stocks]);

  const handleCategoriesChange = useCallback((list) => {
    setCategories(list);
    setActiveCategory((prev) => {
      if (!prev) return prev;
      return list.includes(prev) ? prev : '';
    });
  }, []);

  const stockPagination = useMemo(
    () => ({
      current: stockPage,
      pageSize: stockPageSize,
      total: filteredStocks.length,
      size: 'small',
      showSizeChanger: true,
      pageSizeOptions: ['10', '20', '50', '100'],
      showTotal: (total) => `共 ${total} 条`,
      onChange: (page, pageSize) => {
        setStockPage(page);
        setStockPageSize(pageSize);
      },
    }),
    [stockPage, stockPageSize, filteredStocks.length],
  );

  const categoryTabs = [{ key: '', label: '全部' }, ...categories.map((name) => ({ key: name, label: name }))];

  return (
    <div className="industry-page pool-page">
      <div className="industry-page__header">
        <Title level={3} style={{ margin: 0 }}>
          股票池
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          后选股分类保存在招商证券自定义板块（blocknew）
          {swingsLoading ? ' · 近三日买卖点计算中…' : ''}
        </Text>
      </div>

      <Card title="分类管理" size="small">
        <PoolCategoryManager onChange={handleCategoriesChange} />
      </Card>

      <div className="pool-category-tabs">
        {categoryTabs.map((tab) => (
          <button
            key={tab.key || '__all'}
            type="button"
            className={`pool-category-tab${activeCategory === tab.key ? ' is-active' : ''}`}
            onClick={() => setActiveCategory(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <section className="bankuai-section bankuai-section--stocks industry-body">
        <Card
          title={activeCategory ? `成分股 · ${activeCategory}` : '成分股 · 全部'}
          size="small"
          className="bankuai-panel bankuai-panel--list bankuai-panel--stocks"
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
          ) : (
            <Table
              className="bankuai-stock-table"
              rowKey={(row) => row.ide}
              columns={stockColumns}
              dataSource={filteredStocks}
              pagination={filteredStocks.length > 0 ? stockPagination : false}
              size="small"
              bordered
              scroll={{ x: 1480, y: 420 }}
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
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择成分股" />
          ) : (
            <>
              <PoolCategoryControl ide={selectedStock.ide} compact />
              <StockChart ide={selectedStock.ide} height={260} showSwingMarkersToggle />
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
