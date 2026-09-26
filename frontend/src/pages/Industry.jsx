import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Alert, Card, Empty, Input, Spin, Table, Typography } from 'antd';

import EmbeddedFinanceTabs from '../components/EmbeddedFinanceTabs';
import MarketHeatmap from '../components/MarketHeatmap';
import PoolCategoryControl from '../components/PoolCategoryControl';
import StockChart from '../components/StockChart';
import StockFilterDropdown, {
  ALL_STOCK_FILTERS,
  DEFAULT_STOCK_FILTERS,
} from '../components/StockFilterDropdown';
import { useStockTableColumns } from '../utils/sectorStockColumns';
import { filterStocks } from '../utils/stockFilters';

const { Title, Text } = Typography;

function matchesNameKeyword(row, keyword) {
  const q = keyword.trim().toLowerCase();
  if (!q) return true;
  const name = String(row?.name ?? '').toLowerCase();
  const ide = String(row?.ide ?? '').toLowerCase();
  return name.includes(q) || ide.includes(q);
}

export default function Industry() {
  const { name: sectorName } = useParams();
  const decodedName = decodeURIComponent(sectorName ?? '');

  const [sector, setSector] = useState(null);
  const [loadingSector, setLoadingSector] = useState(true);
  const [sectorError, setSectorError] = useState('');

  const [stocks, setStocks] = useState([]);
  const [loadingStocks, setLoadingStocks] = useState(true);
  const [stockError, setStockError] = useState('');
  const [stockKeyword, setStockKeyword] = useState('');

  const [selectedStock, setSelectedStock] = useState(null);
  const [stockFilters, setStockFilters] = useState(DEFAULT_STOCK_FILTERS);
  const [stockPage, setStockPage] = useState(1);
  const [stockPageSize, setStockPageSize] = useState(20);

  const filteredStocks = useMemo(
    () => filterStocks(stocks, stockFilters).filter((row) => matchesNameKeyword(row, stockKeyword)),
    [stocks, stockFilters, stockKeyword],
  );

  const { columns: stockColumns } = useStockTableColumns({
    onCriteriaChange: () => setStockPage(1),
  });

  useEffect(() => {
    setStockPage(1);
    setSelectedStock(null);
  }, [decodedName, stockFilters, stocks, stockKeyword]);

  const loadSector = useCallback(() => {
    if (!decodedName) return undefined;

    setLoadingSector(true);
    setSectorError('');
    setSector(null);

    return fetch(`/api/hy/${encodeURIComponent(decodedName)}/`)
      .then((res) => {
        if (!res.ok) throw new Error('行业信息加载失败');
        return res.json();
      })
      .then((payload) => {
        setSector(payload);
      })
      .catch((err) => {
        setSectorError(err.message);
      })
      .finally(() => {
        setLoadingSector(false);
      });
  }, [decodedName]);

  const loadStocks = useCallback(() => {
    if (!decodedName) return undefined;

    setLoadingStocks(true);
    setStockError('');
    setStocks([]);
    setStockKeyword('');
    setSelectedStock(null);

    return fetch(`/api/hy/${encodeURIComponent(decodedName)}/stocks/`)
      .then((res) => {
        if (!res.ok) throw new Error('成分股加载失败');
        return res.json();
      })
      .then((payload) => {
        setStocks(payload.stocks ?? []);
      })
      .catch((err) => {
        setStockError(err.message);
      })
      .finally(() => {
        setLoadingStocks(false);
      });
  }, [decodedName]);

  useEffect(() => {
    loadSector();
    loadStocks();
  }, [loadSector, loadStocks]);

  useEffect(() => {
    const titleName = sector?.name || decodedName;
    if (titleName) {
      document.title = `${titleName}行业`;
      return () => {
        document.title = 'Project';
      };
    }
    document.title = '行业';
    return () => {
      document.title = 'Project';
    };
  }, [sector, decodedName]);

  const handleStockFilterChange = (key, checked) => {
    setStockFilters((prev) => ({ ...prev, [key]: checked }));
  };

  const handleToggleAllFilters = (checked) => {
    setStockFilters(checked ? { ...ALL_STOCK_FILTERS } : { ...DEFAULT_STOCK_FILTERS });
  };

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

  const stockCountLabel = `${filteredStocks.length}${
    filteredStocks.length !== stocks.length ? ` / ${stocks.length}` : ''
  }`;

  const sectorTitle = sector?.name || decodedName;
  const sectorIdeLabel = sector?.ide ? `（${sector.ide}）` : '';

  if (!decodedName) {
    return <Alert type="warning" message="未指定行业" showIcon />;
  }

  return (
    <div className="industry-page">
      <div className="industry-page__header">
        <Title level={3} style={{ margin: 0 }}>
          {loadingSector ? '行业' : `${sectorTitle}${sectorIdeLabel}`}
        </Title>
        {sector?.level ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            层级 {sector.level}
            {sector.stock_count != null ? ` · ${sector.stock_count} 只成分股` : ''}
          </Text>
        ) : null}
      </div>

      {sectorError ? (
        <Alert type="error" message={sectorError} showIcon style={{ marginBottom: 12 }} />
      ) : null}

      <Card
        title="行业K线"
        size="small"
        className="industry-chart-card"
        loading={loadingSector}
      >
        {!sector ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无行业数据" />
        ) : !sector.ide ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="该行业暂无指数代码" />
        ) : (
          <StockChart ide={sector.ide} height={300} showFsaContextMenu={false} />
        )}
      </Card>

      <MarketHeatmap
        sector={decodedName}
        title="行业热力图"
        height={480}
        className="industry-heatmap-card"
      />

      <section className="bankuai-section bankuai-section--stocks industry-body">
        <Card
          title="成分股"
          size="small"
          className="bankuai-panel bankuai-panel--list bankuai-panel--stocks"
          extra={
            <StockFilterDropdown
              filters={stockFilters}
              onChange={handleStockFilterChange}
              onToggleAll={handleToggleAllFilters}
            />
          }
        >
          <Text type="secondary" style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
            {sectorTitle}（{stockCountLabel}）
          </Text>
          <Input.Search
            allowClear
            size="small"
            placeholder="搜索股票名称/代码"
            value={stockKeyword}
            onChange={(e) => setStockKeyword(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          {stockError ? (
            <Alert type="error" message={stockError} showIcon style={{ marginBottom: 8 }} />
          ) : null}
          {loadingStocks ? (
            <div className="bankuai-panel__center">
              <Spin />
            </div>
          ) : (
            <Table
              className="bankuai-stock-table"
              rowKey={(row) => row.ide || row.name}
              columns={stockColumns}
              dataSource={filteredStocks}
              pagination={filteredStocks.length > 0 ? stockPagination : false}
              size="small"
              bordered
              scroll={{ x: 1100, y: 420 }}
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
