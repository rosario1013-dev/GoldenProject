import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Breadcrumb, Card, Empty, Input, Radio, Spin, Table, Typography } from 'antd';

import EmbeddedFinanceTabs from '../components/EmbeddedFinanceTabs';
import PoolCategoryControl from '../components/PoolCategoryControl';
import StockChart from '../components/StockChart';
import StockFilterDropdown, {
  ALL_STOCK_FILTERS,
  DEFAULT_STOCK_FILTERS,
} from '../components/StockFilterDropdown';
import { filterStocks } from '../utils/stockFilters';
import { buildSectorChgColumns, IndustryLink, useStockTableColumns } from '../utils/sectorStockColumns';

const { Title, Text } = Typography;

const ROOT_PARENT = '全部行业';

function matchesNameKeyword(row, keyword) {
  const q = keyword.trim().toLowerCase();
  if (!q) return true;
  const name = String(row?.name ?? '').toLowerCase();
  const ide = String(row?.ide ?? '').toLowerCase();
  return name.includes(q) || ide.includes(q);
}

export default function Bankuai() {
  const [breadcrumb, setBreadcrumb] = useState([{ name: ROOT_PARENT, parent: ROOT_PARENT }]);
  const [hyLevel, setHyLevel] = useState('1');
  const [sectors, setSectors] = useState([]);
  const [loadingSectors, setLoadingSectors] = useState(true);
  const [sectorError, setSectorError] = useState('');
  const [sectorKeyword, setSectorKeyword] = useState('');

  const [selectedSector, setSelectedSector] = useState(null);
  const [stocks, setStocks] = useState([]);
  const [loadingStocks, setLoadingStocks] = useState(false);
  const [stockError, setStockError] = useState('');
  const [hasChildren, setHasChildren] = useState(false);
  const [stockKeyword, setStockKeyword] = useState('');

  const [selectedStock, setSelectedStock] = useState(null);
  const [stockFilters, setStockFilters] = useState(DEFAULT_STOCK_FILTERS);
  const [stockPage, setStockPage] = useState(1);
  const [stockPageSize, setStockPageSize] = useState(20);

  const currentParent = breadcrumb[breadcrumb.length - 1].parent;

  const filteredSectors = useMemo(
    () => sectors.filter((row) => matchesNameKeyword(row, sectorKeyword)),
    [sectors, sectorKeyword],
  );

  const filteredStocks = useMemo(
    () => filterStocks(stocks, stockFilters).filter((row) => matchesNameKeyword(row, stockKeyword)),
    [stocks, stockFilters, stockKeyword],
  );

  useEffect(() => {
    setStockPage(1);
  }, [selectedSector, stockFilters, stocks, stockKeyword]);

  const loadSectors = useCallback((parent, level) => {
    setLoadingSectors(true);
    setSectorError('');
    setSectors([]);
    setSectorKeyword('');
    setSelectedSector(null);
    setStocks([]);
    setStockKeyword('');
    setSelectedStock(null);
    setHasChildren(false);

    const params = new URLSearchParams({ parent });
    if (parent === ROOT_PARENT) {
      params.set('level', level);
    }
    return fetch(`/api/hy/?${params}`)
      .then((res) => {
        if (!res.ok) throw new Error('板块列表加载失败');
        return res.json();
      })
      .then((payload) => {
        setSectors(payload.sectors ?? []);
      })
      .catch((err) => {
        setSectorError(err.message);
      })
      .finally(() => {
        setLoadingSectors(false);
      });
  }, []);

  const loadStocks = useCallback((sectorName) => {
    setLoadingStocks(true);
    setStockError('');
    setStocks([]);
    setStockKeyword('');
    setSelectedStock(null);
    setHasChildren(false);

    return fetch(`/api/hy/${encodeURIComponent(sectorName)}/stocks/`)
      .then((res) => {
        if (!res.ok) throw new Error('板块成分股加载失败');
        return res.json();
      })
      .then((payload) => {
        setStocks(payload.stocks ?? []);
        setHasChildren(Boolean(payload.has_children));
      })
      .catch((err) => {
        setStockError(err.message);
      })
      .finally(() => {
        setLoadingStocks(false);
      });
  }, []);

  useEffect(() => {
    loadSectors(currentParent, hyLevel);
  }, [currentParent, hyLevel, loadSectors]);

  const handleHyLevelChange = (e) => {
    const next = e.target.value;
    setHyLevel(next);
    setBreadcrumb([{ name: ROOT_PARENT, parent: ROOT_PARENT }]);
  };

  const handleSectorClick = (sector) => {
    setSelectedSector(sector);
    loadStocks(sector.name);
  };

  const handleDrillDown = (sector) => {
    setBreadcrumb((prev) => [...prev, { name: sector.name, parent: sector.name }]);
  };

  const handleBreadcrumbClick = (index) => {
    setBreadcrumb((prev) => prev.slice(0, index + 1));
  };

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

  const chgColumns = useMemo(() => buildSectorChgColumns(), []);
  const { columns: stockColumns } = useStockTableColumns({
    onCriteriaChange: () => setStockPage(1),
  });

  const sectorColumns = useMemo(
    () => [
      {
        title: '板块名称',
        dataIndex: 'name',
        key: 'name',
        ellipsis: true,
        align: 'center',
        fixed: 'left',
        width: 120,
        render: (name) => <IndustryLink name={name}>{name || '—'}</IndustryLink>,
      },
      ...chgColumns,
      {
        title: '',
        key: 'action',
        width: 44,
        align: 'center',
        fixed: 'right',
        render: (_, row) => (
          <a
            onClick={(e) => {
              e.stopPropagation();
              handleDrillDown(row);
            }}
          >
            子
          </a>
        ),
      },
    ],
    [chgColumns],
  );

  const typeFilteredCount = useMemo(
    () => filterStocks(stocks, stockFilters).length,
    [stocks, stockFilters],
  );

  const stockCountLabel = selectedSector
    ? `${filteredStocks.length}${filteredStocks.length !== typeFilteredCount ? ` / ${typeFilteredCount}` : ''}${
        typeFilteredCount !== stocks.length ? ` / ${stocks.length}` : ''
      }`
    : '—';

  return (
    <div className="bankuai-page">
      <div className="bankuai-page__header">
        <Title level={3} style={{ margin: 0 }}>
          板块
        </Title>
        <Breadcrumb
          items={breadcrumb.map((item, index) => ({
            title:
              index < breadcrumb.length - 1 ? (
                <a onClick={() => handleBreadcrumbClick(index)}>{item.name}</a>
              ) : (
                item.name
              ),
          }))}
        />
      </div>

      <div className="bankuai-layout">
        {/* 上段：行业板块 — 左列表 / 右K线 */}
        <section className="bankuai-section bankuai-section--sectors">
          <Card
            title="行业板块"
            size="small"
            className="bankuai-panel bankuai-panel--list"
            extra={
              <Radio.Group
                size="small"
                optionType="button"
                buttonStyle="solid"
                value={hyLevel}
                onChange={handleHyLevelChange}
                options={[
                  { label: '一级行业', value: '1' },
                  { label: '二级行业', value: '2' },
                ]}
              />
            }
          >
            <Input.Search
              allowClear
              size="small"
              placeholder="搜索行业名称"
              value={sectorKeyword}
              onChange={(e) => setSectorKeyword(e.target.value)}
              style={{ marginBottom: 8 }}
            />
            {sectorError ? (
              <Alert type="error" message={sectorError} showIcon style={{ marginBottom: 8 }} />
            ) : null}
            {loadingSectors ? (
              <div className="bankuai-panel__center">
                <Spin />
              </div>
            ) : (
              <Table
                rowKey={(row) => row.ide || row.name}
                columns={sectorColumns}
                dataSource={filteredSectors}
                pagination={filteredSectors.length > 12 ? { pageSize: 12, size: 'small' } : false}
                size="small"
                bordered
                scroll={{ x: 560 }}
                rowClassName={(row) => (selectedSector?.name === row.name ? 'row-selected' : '')}
                onRow={(row) => ({
                  onClick: () => handleSectorClick(row),
                  style: { cursor: 'pointer' },
                })}
              />
            )}
          </Card>

          <Card
            title={
              selectedSector
                ? `${selectedSector.name}${selectedSector.ide ? `（${selectedSector.ide}）` : ''}`
                : '板块K线'
            }
            size="small"
            className="bankuai-panel bankuai-panel--chart"
          >
            {!selectedSector ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择行业板块" />
            ) : !selectedSector.ide ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="该板块暂无指数代码" />
            ) : (
              <StockChart ide={selectedSector.ide} fillHeight showFsaContextMenu={false} />
            )}
          </Card>
        </section>

        {/* 下段：成分股 — 左列表 / 右K线 */}
        <section className="bankuai-section bankuai-section--stocks">
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
              {selectedSector ? `${selectedSector.name}（${stockCountLabel}）` : '请选择上方板块'}
              {selectedSector && hasChildren ? (
                <>
                  {' '}
                  <a onClick={() => handleDrillDown(selectedSector)}>子行业</a>
                </>
              ) : null}
            </Text>
            <Input.Search
              allowClear
              size="small"
              placeholder="搜索股票名称/代码"
              value={stockKeyword}
              onChange={(e) => setStockKeyword(e.target.value)}
              disabled={!selectedSector}
              style={{ marginBottom: 8 }}
            />
            {stockError ? (
              <Alert type="error" message={stockError} showIcon style={{ marginBottom: 8 }} />
            ) : null}
            {!selectedSector ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择板块" />
            ) : loadingStocks ? (
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
                <div className="bankuai-cw">
                  <EmbeddedFinanceTabs ide={selectedStock.ide} />
                </div>
              </>
            )}
          </Card>
        </section>
      </div>
    </div>
  );
}
