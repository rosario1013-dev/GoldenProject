import { Button, Descriptions, Drawer, Space, Tag, Typography } from 'antd';
import { Link } from 'react-router-dom';

import {
  formatAddedProfit,
  formatContribution,
  formatGrowthPct,
  formatProfit,
  formatScore,
  growthClassName,
  statusLabel,
} from '../../utils/industryProfitFormat';

const { Title, Paragraph, Text } = Typography;

export default function IndustryProfitDetail({ open, row, onClose }) {
  if (!row) {
    return (
      <Drawer open={open} onClose={onClose} width={420} title="行业详情">
        <Text type="secondary">未选择行业</Text>
      </Drawer>
    );
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={440}
      title={row.industry}
      extra={
        <Link to={`/industry/${encodeURIComponent(row.industry)}`}>
          <Button type="primary">查看该行业股票 →</Button>
        </Link>
      }
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={2} className={`ipg-detail__growth ${growthClassName(row.profit_growth_yoy)}`}>
            {formatGrowthPct(row.profit_growth_yoy)}
          </Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            YoY Net Income Growth
            {row.profit_status && row.profit_status !== 'PROFITABLE'
              ? ` · ${statusLabel(row.profit_status)}`
              : ''}
          </Paragraph>
        </div>

        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="Current Profit">
            {formatProfit(row.current_profit)}
          </Descriptions.Item>
          <Descriptions.Item label="3Y CAGR">
            <span className={growthClassName(row.profit_cagr_3y)}>
              {formatGrowthPct(row.profit_cagr_3y)}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="5Y CAGR">
            <span className={growthClassName(row.profit_cagr_5y)}>
              {formatGrowthPct(row.profit_cagr_5y)}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="Added Profit">
            {formatAddedProfit(row.added_profit)}
          </Descriptions.Item>
          <Descriptions.Item label="Contribution">
            {formatContribution(row.profit_contribution)}
          </Descriptions.Item>
          <Descriptions.Item label="Growth Score">{formatScore(row.growth_score)}</Descriptions.Item>
          <Descriptions.Item label="Stability">
            {formatScore(row.growth_stability_score)}
          </Descriptions.Item>
          <Descriptions.Item label="Confidence">
            {formatScore(row.growth_confidence)}
          </Descriptions.Item>
          <Descriptions.Item label="Companies">
            {row.company_count}
            {row.low_sample_size ? <Tag style={{ marginLeft: 8 }}>Low Sample Size</Tag> : null}
          </Descriptions.Item>
          <Descriptions.Item label="Valuation Score">
            {row.valuation_score == null ? '—' : formatScore(row.valuation_score)}
          </Descriptions.Item>
          <Descriptions.Item label="Profit Margin">—</Descriptions.Item>
          <Descriptions.Item label="ROE / ROIC">—</Descriptions.Item>
          <Descriptions.Item label="PE / PB / PS">—</Descriptions.Item>
        </Descriptions>

        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          利润增长与估值交叉分析将在行业级 Valuation Score 就绪后启用。当前可进入行业页查看成分股。
        </Paragraph>
      </Space>
    </Drawer>
  );
}
