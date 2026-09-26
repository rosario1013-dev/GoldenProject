import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Alert, Card, Col, Descriptions, Row, Space, Spin, Tabs, Tag } from 'antd';

import CwTable from '../components/CwTable';
import FinanceTrendCharts from '../components/FinanceTrendCharts';
import PoolCategoryControl from '../components/PoolCategoryControl';
import StockChart from '../components/StockChart';
import StockReports from '../components/StockReports';
import StockIndependentStrongRelation from '../components/StockIndependentStrongRelation';

const FIELD_ORDER = [
  { key: 'IDS', label: '名称' },
  { key: 'ID6', label: '证券代码' },
  { key: 'DQ', label: '地区' },
  { key: 'HY1', label: '一级行业' },
  { key: 'HY2', label: '二级行业' },
  { key: 'BK_GN', label: '概念' },
];

const INDUSTRY_LINK_FIELDS = new Set(['HY1', 'HY2']);

function formatTuple(value) {
  if (!Array.isArray(value)) return String(value ?? '-');
  if (value.length === 0) return '-';
  const [name, code] = value;
  return code ? `${name} (${code})` : name;
}

function industryName(value) {
  if (Array.isArray(value) && value[0]) return String(value[0]);
  if (typeof value === 'string' && value.trim()) return value.trim();
  return '';
}

function formatConcepts(value) {
  if (!Array.isArray(value) || value.length === 0) return '—';
  return (
    <Space size={[4, 4]} wrap>
      {value.map((item, index) => {
        const name = Array.isArray(item) ? item[0] : item;
        if (!name) return null;
        return (
          <Tag key={`${name}-${index}`} style={{ marginInlineEnd: 0 }}>
            {name}
          </Tag>
        );
      })}
    </Space>
  );
}

function formatFieldValue(key, value) {
  if (key === 'BK_GN') return formatConcepts(value);
  if (INDUSTRY_LINK_FIELDS.has(key)) {
    const name = industryName(value);
    if (!name) return '—';
    const code = Array.isArray(value) && value[1] ? value[1] : '';
    return (
      <Link to={`/industry/${encodeURIComponent(name)}`} target="_blank" rel="noopener noreferrer">
        {code ? `${name} (${code})` : name}
      </Link>
    );
  }
  if (value === undefined || value === null || value === '') return '—';
  return formatTuple(value);
}

function BasicInfo({ data }) {
  const items = FIELD_ORDER.map(({ key, label }) => ({
    key,
    label,
    span: key === 'BK_GN' ? 2 : 1,
    children: formatFieldValue(key, data[key]),
  }));

  return <Descriptions bordered column={2} size="small" items={items} />;
}

export default function StockDetail() {
  const { ide } = useParams();
  const [stock, setStock] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    setStock(null);

    fetch(`/api/stock/${encodeURIComponent(ide)}/`)
      .then((res) => {
        if (!res.ok) throw new Error('股票不存在或加载失败');
        return res.json();
      })
      .then((data) => {
        if (!cancelled) setStock(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ide]);

  useEffect(() => {
    if (stock?.IDS) {
      document.title = stock.IDS;
      return () => {
        document.title = 'Project';
      };
    }
    document.title = ide ? `${ide} - Project` : 'Project';
    return () => {
      document.title = 'Project';
    };
  }, [stock, ide]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return <Alert type="error" message={error} showIcon />;
  }

  return (
    <div>
      <Row gutter={[16, 16]} align="stretch" className="stock-detail-info-row">
        <Col xs={24} lg={16}>
          <Card title="股票信息" size="small" className="stock-detail-info-card">
            <BasicInfo data={stock} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="后选股" size="small" className="stock-detail-pool-card">
            <PoolCategoryControl ide={ide} compact />
          </Card>
        </Col>
      </Row>

      <Card title="FDK 行情图" size="small" style={{ marginTop: 16 }}>
        <StockChart ide={ide} height={480} showIndicators />
      </Card>

      <Card size="small" style={{ marginTop: 16 }} styles={{ body: { paddingTop: 8 } }}>
        <Tabs
          defaultActiveKey="cw"
          items={[
            {
              key: 'cw',
              label: '财务报表',
              children: <CwTable ide={ide} embedded showControlsWhenEmbedded />,
            },
            {
              key: 'trend',
              label: '财务趋势',
              children: <FinanceTrendCharts ide={ide} embedded />,
            },
            {
              key: 'reports',
              label: '研究报告',
              children: <StockReports ide={ide} embedded />,
            },
            {
              key: 'independent-strong',
              label: '独立走强（指数）',
              children: <StockIndependentStrongRelation ide={ide} embedded />,
            },
          ]}
        />
      </Card>
    </div>
  );
}
