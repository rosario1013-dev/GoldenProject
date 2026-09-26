import { useEffect, useMemo, useState } from 'react';
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
  Switch,
  Table,
  Tooltip,
  Typography,
  message,
} from 'antd';
import { CheckOutlined, CloseOutlined, SearchOutlined } from '@ant-design/icons';

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

export default function AiAdvice() {
  const [industries, setIndustries] = useState([ALL_INDUSTRIES]);
  const [industryOptions, setIndustryOptions] = useState([]);
  const [poolCategories, setPoolCategories] = useState([]);
  const [poolCategory, setPoolCategory] = useState(undefined);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [modelInfo, setModelInfo] = useState(null);

  const [pMin, setPMin] = useState(0.35);
  const [limit, setLimit] = useState(50);
  const [topK, setTopK] = useState(200);
  const [requireChannel, setRequireChannel] = useState(false);
  const [dropAnomaly, setDropAnomaly] = useState(true);

  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');
  const [disclaimer, setDisclaimer] = useState('');
  const [filterStats, setFilterStats] = useState(null);
  const [keyword, setKeyword] = useState('');
  const [selectedStock, setSelectedStock] = useState(null);
  const [stockFilters, setStockFilters] = useState(DEFAULT_STOCK_FILTERS);

  useEffect(() => {
    let cancelled = false;
    setLoadingMeta(true);
    Promise.all([
      fetch('/api/hy/?level=1').then((res) => (res.ok ? res.json() : { sectors: [] })),
      fetch('/api/pool/categories/').then((res) => (res.ok ? res.json() : { categories: [] })),
      fetch('/api/ai/advice/models/').then((res) => (res.ok ? res.json() : { ready: false })),
    ])
      .then(([hy, pool, models]) => {
        if (cancelled) return;
        const level1 = (hy.sectors ?? []).map((sector) => ({
          value: sector.name,
          label: sector.ide ? `${sector.name}（${sector.ide}）` : sector.name,
        }));
        setIndustryOptions([{ value: ALL_INDUSTRIES, label: '全部行业' }, ...level1]);
        setPoolCategories(
          (pool.categories ?? []).map((item) => ({
            value: typeof item === 'string' ? item : item.category || item.name,
            label: typeof item === 'string' ? item : item.category || item.name,
          })),
        );
        setModelInfo(models);
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
      // Newly selected「全部行业」→ exclusive
      setIndustries([ALL_INDUSTRIES]);
      return;
    }
    if (next.includes(ALL_INDUSTRIES) && next.length > 1) {
      // Picked specific industries while「全部行业」was on → drop all
      setIndustries(next.filter((name) => name !== ALL_INDUSTRIES));
      return;
    }
    setIndustries(next);
  };

  const filteredStocks = useMemo(
    () => filterStocks(stocks, stockFilters).filter((row) => matchesKeyword(row, keyword)),
    [stocks, stockFilters, keyword],
  );

  const { columns: baseColumns, rangeSortColumn } = useStockTableColumns({
    defaultSort: { key: 'score', order: 'descend' },
  });

  const columns = useMemo(() => {
    const base = baseColumns;
    return [
      ...base.slice(0, 2),
      rangeSortColumn({
        title: '综合分',
        dataIndex: 'score',
        key: 'score',
        width: 84,
        render: (value) => (value == null ? '—' : Number(value).toFixed(3)),
      }),
      rangeSortColumn({
        title: '买入概率',
        dataIndex: 'signal_prob',
        key: 'signal_prob',
        width: 88,
        render: (value) => (value == null ? '—' : Number(value).toFixed(3)),
      }),
      rangeSortColumn({
        title: 'XGB对照',
        dataIndex: 'xgb_prob',
        key: 'xgb_prob',
        width: 84,
        render: (value) => (value == null ? '—' : Number(value).toFixed(3)),
      }),
      rangeSortColumn({
        title: 'Rank',
        dataIndex: 'rank_score',
        key: 'rank_score',
        width: 72,
        render: (value) => (value == null ? '—' : Number(value).toFixed(3)),
      }),
      {
        title: '通道',
        dataIndex: 'channel_score_text',
        key: 'channel_score_text',
        width: 74,
        align: 'center',
        render: (value, row) => (
          <Tooltip title={(row.reasons || []).join('；')}>
            <span>{value || '—'}</span>
          </Tooltip>
        ),
      },
      {
        title: '异常',
        dataIndex: 'is_anomaly',
        key: 'is_anomaly',
        width: 64,
        align: 'center',
        render: (value) => (value ? '是' : '否'),
      },
      ...base.slice(2),
    ];
  }, [baseColumns, rangeSortColumn]);

  const handleScan = () => {
    if (!industries.length && !poolCategory) {
      message.warning('请至少选择一个行业或股票池');
      return;
    }
    setLoading(true);
    setSearched(true);
    setError('');
    setSelectedStock(null);
    setFilterStats(null);

    const scanAll = industries.includes(ALL_INDUSTRIES);
    fetch('/api/ai/advice/scan/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        industries: scanAll ? [ALL_INDUSTRIES] : industries,
        pool_category: poolCategory || null,
        p_min: pMin,
        limit,
        top_k: topK,
        require_channel: requireChannel,
        drop_anomaly: dropAnomaly,
      }),
    })
      .then(async (res) => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(payload.error || `AI 建议扫描失败（HTTP ${res.status}）`);
        return payload;
      })
      .then((payload) => {
        setStocks(payload.stocks ?? []);
        setDisclaimer(payload.disclaimer || '');
        setFilterStats(payload.stats || null);
        const count = payload.count ?? 0;
        if (count === 0 && payload.stats) {
          const s = payload.stats;
          message.warning(
            `找到 0 只建议（候选${s.candidates} / 信号${s.after_signal} / 异常后${s.after_anomaly} / 通道${s.after_channel}）`,
          );
        } else {
          message.success(`找到 ${count} 只建议`);
        }
      })
      .catch((err) => {
        setStocks([]);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  };

  const handleConfirm = (action) => {
    if (!selectedStock?.ide) return;
    setConfirming(true);
    fetch('/api/ai/advice/confirm/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ide: selectedStock.ide,
        action,
        score: selectedStock.score,
        payload: {
          signal_prob: selectedStock.signal_prob,
          rank_score: selectedStock.rank_score,
          reasons: selectedStock.reasons,
        },
      }),
    })
      .then(async (res) => {
        const payload = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(payload.error || '确认失败');
        return payload;
      })
      .then(() => {
        message.success(action === 'buy' ? '已记录关注意向' : '已记录跳过');
      })
      .catch((err) => message.error(err.message))
      .finally(() => setConfirming(false));
  };

  return (
    <div className="industry-page">
      <div className="industry-page__header">
        <Title level={3} style={{ margin: 0 }}>
          AI 买入建议
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          LightGBM 选股/信号 + 上升通道确认 + 异常检测；建议需人工确认，不下单
        </Text>
      </div>

      {modelInfo && !modelInfo.ready ? (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message="模型未就绪"
          description={`缺少：${(modelInfo.missing || []).join('、') || '未知'}。请先运行 python -m GP_AI train-all`}
        />
      ) : null}

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
          <div>
            <Text strong style={{ display: 'block', marginBottom: 6 }}>
              股票池分类（可选）
            </Text>
            <Select
              allowClear
              showSearch
              placeholder="不选则不限股票池"
              style={{ width: '100%' }}
              options={poolCategories}
              value={poolCategory}
              onChange={setPoolCategory}
              optionFilterProp="label"
            />
          </div>
          <Space wrap>
            <Text>买入概率 ≥</Text>
            <InputNumber
              min={0}
              max={1}
              step={0.05}
              value={pMin}
              onChange={(value) => setPMin(value ?? 0.35)}
            />
            <Text>Top-K</Text>
            <InputNumber min={10} max={2000} value={topK} onChange={(value) => setTopK(value ?? 200)} />
            <Text>最多返回</Text>
            <InputNumber min={1} max={500} value={limit} onChange={(value) => setLimit(value ?? 50)} />
            <Text>要求上升通道</Text>
            <Switch checked={requireChannel} onChange={setRequireChannel} />
            <Text>剔除异常</Text>
            <Switch checked={dropAnomaly} onChange={setDropAnomaly} />
            <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleScan}>
              开始扫描
            </Button>
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            默认不强制上升通道（通道仍计入评分）。若结果为 0，可下调买入概率阈值或关闭「要求上升通道」。
          </Text>
          {disclaimer ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {disclaimer}
            </Text>
          ) : null}
          {filterStats ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              过滤进度：宇宙 {filterStats.universe} → 特征 {filterStats.with_features} → 候选{' '}
              {filterStats.candidates} → 信号 {filterStats.after_signal} → 异常后 {filterStats.after_anomaly} →
              通道 {filterStats.after_channel} → 返回 {filterStats.returned}
            </Text>
          ) : null}
        </Space>
      </Card>

      <section className="bankuai-section bankuai-section--stocks industry-body">
        <Card
          title={`建议结果${searched ? `（${filteredStocks.length}）` : ''}`}
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
          extra={
            selectedStock ? (
              <Space>
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  loading={confirming}
                  onClick={() => handleConfirm('buy')}
                >
                  确认关注
                </Button>
                <Button
                  icon={<CloseOutlined />}
                  loading={confirming}
                  onClick={() => handleConfirm('skip')}
                >
                  跳过
                </Button>
              </Space>
            ) : null
          }
        >
          {!selectedStock ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择建议结果中的股票" />
          ) : (
            <>
              <Space wrap style={{ marginBottom: 8 }}>
                <Text type="secondary">综合分 {selectedStock.score?.toFixed?.(3) ?? '—'}</Text>
                <Text type="secondary">买入概率 {selectedStock.signal_prob?.toFixed?.(3) ?? '—'}</Text>
                <Text type="secondary">
                  {(selectedStock.reasons || []).slice(0, 3).join('；') || '—'}
                </Text>
              </Space>
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
