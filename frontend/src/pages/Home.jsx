import { useState } from 'react';
import { Card, Tabs, Typography } from 'antd';

import MarketHeatmap from '../components/MarketHeatmap';
import StockChart, { CHART_PERIODS } from '../components/StockChart';

const { Title } = Typography;

const INDEX_PERIODS = CHART_PERIODS.filter((item) =>
  ['daily', 'weekly', 'monthly'].includes(item.value),
);

const HOME_INDICES = [
  { ide: 'sh000001', name: '上证指数' },
  { ide: 'sz399001', name: '深证成指' },
  { ide: 'sz399006', name: '创业板指' },
  { ide: 'sh000300', name: '沪深300' },
];

export default function Home() {
  const [activeIde, setActiveIde] = useState(HOME_INDICES[0].ide);
  const active = HOME_INDICES.find((item) => item.ide === activeIde) ?? HOME_INDICES[0];

  return (
    <div className="home-page">
      <Title level={2} style={{ marginBottom: 12 }}>
        首页
      </Title>

      <Card size="small" className="home-index-card">
        <Tabs
          activeKey={activeIde}
          onChange={setActiveIde}
          items={HOME_INDICES.map((item) => ({
            key: item.ide,
            label: item.name,
          }))}
        />
        <StockChart
          key={active.ide}
          ide={active.ide}
          height={420}
          periods={INDEX_PERIODS}
          adjustment="none"
        />
      </Card>

      <MarketHeatmap
        title="A股市场热力图"
        height={560}
        className="home-heatmap-card"
        showViewModes
      />
    </div>
  );
}
