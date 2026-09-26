import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Card, Col, Empty, Row, Select, Spin, Table, Typography } from 'antd';

import CompareRatioCell from '../../components/CompareRatioCell';
import StockChart from '../../components/StockChart';
import { COMPARE_CHG_FIELDS, COMPARE_FSA_FIELDS } from '../../utils/compareRatios';
import { IndustryLink } from '../../utils/sectorStockColumns';

const { Title, Text } = Typography;

const MAX_STOCKS = 6;

function stockLabel(stock) {
  const name = stock?.name || '';
  const abb = stock?.ABB || '';
  const ide = stock?.ide || '';
  return [name, abb, ide].filter(Boolean).join(' ');
}

export default function StockCompare() {
  const [stockOptions, setStockOptions] = useState([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [selectedIdes, setSelectedIdes] = useState([]);
  const [rows, setRows] = useState([]);
  const [benchmarks, setBenchmarks] = useState({});
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoadingOptions(true);
    fetch('/api/stocks/')
      .then((res) => (res.ok ? res.json() : { stocks: [] }))
      .then((payload) => {
        if (!cancelled) setStockOptions(payload.stocks ?? []);
      })
      .catch(() => {
        if (!cancelled) setStockOptions([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingOptions(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadCompare = useCallback((ides) => {
    if (!ides.length) {
      setRows([]);
      setBenchmarks({});
      setError('');
      return undefined;
    }

    let cancelled = false;
    setLoadingCompare(true);
    setError('');

    fetch('/api/compare/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ides }),
    })
      .then(async (res) => {
        if (!res.ok) {
          let message = '对比数据加载失败';
          try {
            const payload = await res.json();
            if (payload?.error) message = payload.error;
          } catch {
            // ignore
          }
          throw new Error(message);
        }
        return res.json();
      })
      .then((payload) => {
        if (cancelled) return;
        setRows(payload.stocks ?? []);
        setBenchmarks(payload.benchmarks ?? {});
      })
      .catch((err) => {
        if (!cancelled) {
          setRows([]);
          setBenchmarks({});
          setError(err.message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingCompare(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => loadCompare(selectedIdes), [selectedIdes, loadCompare]);

  const selectOptions = useMemo(
    () =>
      stockOptions.map((stock) => ({
        value: stock.ide,
        label: stockLabel(stock),
      })),
    [stockOptions],
  );

  const ratioColumns = useMemo(() => {
    const fields = [...COMPARE_FSA_FIELDS, ...COMPARE_CHG_FIELDS];
    return fields.map((field) => ({
      title: (
        <div className="compare-table__head">
          <div>{field.label}</div>
          {benchmarks[field.key] != null ? (
            <Text type="secondary" className="compare-table__bench">
              中位 {formatBench(benchmarks[field.key], field.percent)}
            </Text>
          ) : null}
        </div>
      ),
      dataIndex: field.key,
      key: field.key,
      width: 108,
      align: 'center',
      render: (value) => (
        <CompareRatioCell value={value} benchmark={benchmarks[field.key]} percent={field.percent} />
      ),
    }));
  }, [benchmarks]);

  const columns = useMemo(
    () => [
      {
        title: '股票',
        dataIndex: 'name',
        key: 'name',
        fixed: 'left',
        width: 120,
        render: (name, row) => (
          <div className="compare-table__stock">
            <div>{name || '—'}</div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {row.ide}
            </Text>
          </div>
        ),
      },
      {
        title: '报告期',
        dataIndex: 'REPORTDATE',
        key: 'REPORTDATE',
        width: 100,
        align: 'center',
        render: (value) => (value ? String(value).slice(0, 10) : '—'),
      },
      {
        title: '一级行业',
        key: 'HY1',
        width: 96,
        align: 'center',
        render: (_, row) => {
          const hy1 = row.HY1;
          const name = Array.isArray(hy1) ? hy1[0] : null;
          return name ? <IndustryLink name={name}>{name}</IndustryLink> : '—';
        },
      },
      ...ratioColumns,
    ],
    [ratioColumns],
  );

  return (
    <div className="stock-compare-page">
      <Title level={2} style={{ marginTop: 0 }}>
        股票对比
      </Title>
      <Text type="secondary">
        选择多只股票，对比最新财务比率与涨幅。数值相对组内中位数显示「超前 / 落后」标签。
      </Text>

      <Card title="选择对比股票" size="small" style={{ marginTop: 16 }}>
        <Select
          mode="multiple"
          showSearch
          allowClear
          virtual
          maxCount={MAX_STOCKS}
          style={{ width: '100%' }}
          placeholder={`搜索并选择股票，最多 ${MAX_STOCKS} 只`}
          loading={loadingOptions}
          value={selectedIdes}
          options={selectOptions}
          optionFilterProp="label"
          onChange={(values) => setSelectedIdes(values)}
        />
        <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
          已选 {selectedIdes.length} / {MAX_STOCKS} 只
        </Text>
      </Card>

      <Card title="K线对比" size="small" style={{ marginTop: 12 }}>
        {!selectedIdes.length ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择股票后查看K线" />
        ) : loadingCompare ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin />
          </div>
        ) : (
          <Row gutter={[12, 12]}>
            {rows.map((stock) => (
              <Col key={stock.ide} xs={24} lg={12}>
                <Card
                  type="inner"
                  size="small"
                  title={`${stock.name || stock.ide}（${stock.ide}）`}
                  className="compare-chart-card"
                >
                  <StockChart ide={stock.ide} height={240} />
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Card>

      <Card title="比率对比" size="small" style={{ marginTop: 12 }}>
        {error ? <Alert type="error" message={error} showIcon style={{ marginBottom: 12 }} /> : null}
        {!selectedIdes.length ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请先选择要对比的股票" />
        ) : loadingCompare ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin />
          </div>
        ) : (
          <Table
            className="compare-table"
            rowKey="ide"
            size="small"
            bordered
            pagination={false}
            scroll={{ x: 'max-content' }}
            columns={columns}
            dataSource={rows}
          />
        )}
      </Card>
    </div>
  );
}

function formatBench(value, percent) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const num = Number(value);
  if (percent) return `${num.toFixed(2)}%`;
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
}
